"""Durable local UI queue. Workers, not persisted PIDs, own execution leases."""
from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

from .pipeline import Config
from .storage import read_json, write_json
from .ui_process import contained_processes


def utc():
    return datetime.now(timezone.utc).isoformat()


class Lease:
    """Process-lifetime OS lock; an abandoned file is not an active lock."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        if not self.path.stat().st_size:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self.stream = stream
        return True

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None

    def __enter__(self):
        if not self.acquire():
            raise ValueError("store_already_in_use")
        return self

    def __exit__(self, *args):
        self.close()


def execution_busy(root):
    lease = Lease(Path(root) / "execution.lease")
    if not lease.acquire():
        return True
    lease.close()
    return contained_processes(root)


def owns_execution(root, job_id):
    try:
        return read_json(Path(root) / "worker-owner.json")["id"] == job_id and execution_busy(root)
    except FileNotFoundError:
        return False


def job_folder(root, job_id):
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("unknown_job")
    folder = Path(root) / "jobs" / job_id
    if folder.resolve().parent != (Path(root) / "jobs").resolve() or folder.is_symlink():
        raise ValueError("unsafe_job_path")
    return folder


ACTIVE = {"starting", "running"}
TERMINAL = {"complete", "partial", "failed", "cancelled", "interrupted", "needs_attention"}


class Manager:
    def __init__(self, root, config, command=None, autostart=True):
        config.validate()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.command = command or (lambda folder: [sys.executable, "-m", "reel_to_md.ui_worker", str(folder)])
        self.lease = Lease(self.root / "manager.lease")
        if not self.lease.acquire():
            raise ValueError("local_ui_already_running_for_store")
        self.mutex = threading.RLock()
        self.stop_event = threading.Event()
        self.process = None
        self.thread = threading.Thread(target=self._loop, daemon=True)
        if autostart:
            self.start()

    def start(self):
        self.thread.start()

    def read(self, job_id):
        return read_json(job_folder(self.root, job_id) / "job.json")

    def rows(self):
        result = []
        for path in (self.root / "jobs").glob("*/job.json"):
            try:
                result.append(self.read(path.parent.name))
            except (OSError, ValueError, KeyError):
                continue
        return sorted(result, key=lambda row: row["created_utc"], reverse=True)

    def add(self, folder, name, sha256):
        row = {"id": folder.name, "name": name, "input_sha256": sha256,
               "created_utc": utc(), "updated_utc": utc(), "status": "queued",
               "message": "Waiting for the local worker.", "config": asdict(self.config),
               "attempts": [], "pipeline": None, "attempt": None, "retry_ambiguous": False}
        with self.mutex:
            write_json(folder / "job.json", row)
        return row

    def cancel(self, job_id):
        with self.mutex:
            row = self.read(job_id)
            folder = job_folder(self.root, job_id)
            if row["status"] == "queued":
                row.update(status="cancelled", message="Cancelled before processing.", updated_utc=utc())
                write_json(folder / "job.json", row)
            elif row["status"] in ACTIVE:
                write_json(folder / "stop.json", {"status": "cancelled"})
            else:
                raise ValueError("job_is_not_active")

    def resume(self, job_id, acknowledge=False):
        with self.mutex:
            row = self.read(job_id)
            if row["status"] not in {"failed", "cancelled", "interrupted", "needs_attention"}:
                raise ValueError("job_is_not_recoverable")
            if (row.get("pipeline") or {}).get("validation") == "failed":
                raise ValueError("draft_failed_validation_requires_review_or_new_configuration")
            if owns_execution(self.root, job_id):
                raise ValueError("worker_still_stopping")
            if os.name != "nt" and row["status"] in {"interrupted", "cancelled"} and not acknowledge:
                raise ValueError("interrupted_processes_require_acknowledgment")
            row.update(status="queued", message="Recovery queued; completed stages will be checked and reused.",
                       updated_utc=utc(), retry_ambiguous=acknowledge)
            folder = job_folder(self.root, job_id)
            (folder / "stop.json").unlink(missing_ok=True)
            write_json(folder / "job.json", row)

    def tick(self):
        with self.mutex:
            if self.process and self.process.poll() is None:
                return
            self.process = None
            if execution_busy(self.root):
                return  # An earlier server's worker still owns this store.
            rows = self.rows()
            for row in rows:
                if row["status"] in ACTIVE:
                    row.update(status="interrupted", message="Worker stopped. Recover this job to reuse completed stages.", updated_utc=utc())
                    write_json(job_folder(self.root, row["id"]) / "job.json", row)
            queued = [r for r in reversed(rows) if r["status"] == "queued"]
            if not queued:
                return
            row = queued[0]
            folder = job_folder(self.root, row["id"])
            row.update(status="starting", message="Starting the local worker.", updated_utc=utc())
            write_json(folder / "job.json", row)
            options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            try:
                with (folder / "worker.log").open("ab") as log:
                    self.process = subprocess.Popen(self.command(folder), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                                    env={**os.environ, "REEL_TO_MD_UI_WORKER": "1"}, **options)
            except OSError:
                row.update(status="failed", message="Could not start the local worker.", updated_utc=utc())
                write_json(folder / "job.json", row)

    def _loop(self):
        while not self.stop_event.wait(0.5):
            try:
                self.tick()
            except (OSError, ValueError, KeyError):
                # Leave durable records available for recovery after disk issues.
                continue

    def close(self, stop_workers=True):
        self.stop_event.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=3)
        if stop_workers:
            with self.mutex:
                for row in self.rows():
                    if row["status"] in ACTIVE:
                        write_json(job_folder(self.root, row["id"]) / "stop.json", {"status": "interrupted"})
        if self.process:
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass  # Never kill an unrelated or re-used persisted PID.
        self.lease.close()
