"""One isolated UI job. Cancellation stops this worker and its child tree."""
from dataclasses import asdict
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from .pipeline import Config, run_video, versions
from .storage import digest, file_hash, read_json, write_json
from .ui_jobs import Lease, utc
from .ui_process import contain_worker


def stop_tree():
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(os.getpid()), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=8)
        finally:
            os._exit(130)
    os.killpg(os.getpgrp(), signal.SIGKILL)


def main(folder):
    folder = Path(folder).resolve()
    root = folder.parent.parent
    with Lease(root / "execution.lease"):
        if os.environ.get("REEL_TO_MD_UI_WORKER") == "1":
            contain_worker(root)
        row = read_json(folder / "job.json")
        write_json(root / "worker-owner.json", {"id": row["id"]})
        mutex = threading.RLock()
        done = threading.Event()
        stopping = threading.Event()

        def save(**changes):
            with mutex:
                if stopping.is_set() and changes.get("status") not in {"cancelled", "interrupted"}:
                    return
                row.update(changes, updated_utc=utc())
                write_json(folder / "job.json", row)

        def watch():
            while not done.wait(0.2):
                if (folder / "stop.json").exists():
                    stopping.set()
                    try:
                        request = read_json(folder / "stop.json")
                        status = request.get("status")
                        if status not in {"cancelled", "interrupted"}:
                            status = "interrupted"
                        save(status=status, message="Stopped. Completed stages are saved; a shared model request may still be finishing.")
                    finally:
                        stop_tree()

        threading.Thread(target=watch, daemon=True).start()
        try:
            save(status="running", message="Checking the local input and model configuration.")
            config = Config(**row["config"])
            config.validate()
            video = folder / "input.video"
            if file_hash(video) != row["input_sha256"]:
                raise ValueError("uploaded_video_changed")
            identity = digest({"source": row["input_sha256"], "config": asdict(config), "versions": versions(config)})
            pipeline_folder = root / "pipeline" / identity
            pending = [p for p in (pipeline_folder / "model-cache").glob("*.pending") if not p.with_suffix(".json").exists()]
            if pending and not row["retry_ambiguous"]:
                save(status="needs_attention", message="An earlier model request has an unknown outcome. Wait for it to finish, then explicitly allow a new local request.")
                return
            if (pipeline_folder / "active.lock").exists() and row.get("pipeline_job") != identity:
                raise ValueError("unowned_pipeline_lock")
            recovery = pipeline_folder / "recovery" / uuid.uuid4().hex
            if pending or (pipeline_folder / "active.lock").exists():
                recovery.mkdir(parents=True)
                write_json(recovery / "record.json", {"utc": utc(), "explicit_retry_acknowledged": row["retry_ambiguous"], "ui_job": row["id"]})
                for marker in pending:
                    for artifact in marker.parent.glob(marker.stem + ".*"):
                        artifact.rename(recovery / artifact.name)
                lock = pipeline_folder / "active.lock"
                if lock.exists():
                    lock.rename(recovery / "active.lock")

            def progress(attempt, record):
                with mutex:
                    value = str(attempt)
                    if value.startswith("\\\\?\\UNC\\"):
                        value = "\\\\" + value[8:]
                    elif value.startswith("\\\\?\\"):
                        value = value[4:]
                    relative = str(Path(value).relative_to(root))
                    if relative not in row["attempts"]:
                        row["attempts"].append(relative)
                    save(attempt=relative, pipeline_job=record["job_id"], pipeline=record,
                         message="Processing locally. Long model stages show elapsed time, not an estimated percentage.")

            attempt, record = run_video(video, root / "pipeline", config, on_progress=progress)
            save(status=record["state"], pipeline=record, message="Draft ready for review." if record["validation"] == "passed" else "Processing failed. Completed stages and original diagnostics are saved.")
        except Exception as exc:
            save(status="failed", message="Local job failed (" + type(exc).__name__ + "). Check configuration or recover saved work.")
        finally:
            done.set()


if __name__ == "__main__":
    os.environ["REEL_TO_MD_UI_WORKER"] = "1"
    main(sys.argv[1])
