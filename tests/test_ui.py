"""Local UI boundaries, durable recovery, cancellation, and real HTTP tests."""
from dataclasses import asdict
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

import pytest

from reel_to_md import media, ui_worker
from reel_to_md.contracts import render_markdown
from reel_to_md.pipeline import Config, run_video
from reel_to_md.storage import digest, file_hash, read_json, write_json, write_text
from reel_to_md.ui import LIMIT, Manager, Server, attempt_path, public_job, result
from reel_to_md.ui_jobs import Lease, execution_busy, job_folder


@pytest.fixture
def manager(tmp_path):
    manager = Manager(tmp_path / "ui", Config(input_kind="synthetic_fixture"))
    manager.stop_event.set()
    manager.thread.join(timeout=2)
    yield manager
    manager.close()


def add_job(manager, name="fixture.mp4"):
    folder = job_folder(manager.root, uuid.uuid4().hex)
    folder.mkdir(parents=True)
    (folder / "input.video").write_bytes(b"synthetic fixture")
    return manager.add(folder, name, file_hash(folder / "input.video"))


@pytest.fixture
def stub_pipeline(monkeypatch):
    version = lambda config: {"source_sha256": "synthetic-version"}
    monkeypatch.setattr("reel_to_md.pipeline.versions", version)
    monkeypatch.setattr(ui_worker, "versions", version)
    monkeypatch.setattr(media, "probe", lambda path: {"duration": 2, "has_audio": False})
    def frames(path, directory, *args):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "frame.png").write_bytes(b"synthetic pixels")
        return {"frames": [{"file": "frame.png", "seconds": 0, "sha256": file_hash(directory / "frame.png")}], "truncated": False}
    monkeypatch.setattr(media, "frames", frames)
    monkeypatch.setattr(media, "ocr", lambda *args: [{"start_seconds": 0, "end_seconds": 0, "text": '<script>alert("untrusted")</script> python exact.py', "review_flag": "normal"}])


def test_worker_progress_result_and_safe_replay(manager, stub_pipeline, monkeypatch):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    ui_worker.main(folder)
    first = manager.read(row["id"])
    assert first["status"] == "partial" and first["pipeline"]["validation"] == "passed"
    assert first["pipeline"]["current_stage"] is None
    assert len(first["attempts"]) == 1
    data = result(manager.root, first)
    assert '<script>' in data["markdown"] and '```' in data["markdown"]
    assert data["review_status"] == "unreviewed"
    assert data["evidence"]["channels"]["vision"] == "failed"
    manager.read(row["id"])
    first["status"] = "interrupted"
    write_json(folder / "job.json", first)
    # A completed OCR stage must never dispatch again on recovery.
    monkeypatch.setattr(media, "ocr", lambda *args: pytest.fail("duplicate extraction"))
    manager.resume(row["id"], acknowledge=os.name != "nt")
    ui_worker.main(folder)
    replay = manager.read(row["id"])
    assert replay["status"] == "partial" and len(replay["attempts"]) == 2
    assert replay["attempt"] != first["attempt"]
    assert all(s["cache_hit"] for s in replay["pipeline"]["stages"] if s["status"] == "success")
    assert replay["pipeline"]["input_tokens"] == replay["pipeline"]["output_tokens"] == 0
    assert result(manager.root, replay)["markdown"] == data["markdown"]


def test_ambiguous_requests_pause_and_explicit_recovery_archives(manager, stub_pipeline, monkeypatch):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    ui_worker.main(folder)
    row = manager.read(row["id"])
    pipeline = manager.root / "pipeline" / row["pipeline_job"]
    (pipeline / "model-cache").mkdir()
    (pipeline / "model-cache/vision-0.pending").write_text("unknown outcome")
    (pipeline / "model-cache/vision-0.first-response.txt").write_text("preserved failure")
    (pipeline / "active.lock").write_text("interrupted")
    row["status"] = "interrupted"
    write_json(folder / "job.json", row)
    manager.resume(row["id"], acknowledge=os.name != "nt")
    original = ui_worker.run_video
    monkeypatch.setattr(ui_worker, "run_video", lambda *args, **kwargs: pytest.fail("ambiguous request dispatched"))
    ui_worker.main(folder)
    assert manager.read(row["id"])["status"] == "needs_attention"
    assert (pipeline / "model-cache/vision-0.pending").exists()
    manager.resume(row["id"], acknowledge=True)
    monkeypatch.setattr(ui_worker, "run_video", original)
    ui_worker.main(folder)
    assert manager.read(row["id"])["status"] == "partial"
    archives = list((pipeline / "recovery").glob("*"))
    assert len(archives) == 1
    assert (archives[0] / "vision-0.pending").read_text() == "unknown outcome"
    assert (archives[0] / "vision-0.first-response.txt").read_text() == "preserved failure"
    assert (archives[0] / "active.lock").read_text() == "interrupted"
    assert read_json(archives[0] / "record.json")["explicit_retry_acknowledged"] is True


def test_server_restart_does_not_start_over_live_worker(manager, monkeypatch):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    row["status"] = "running"
    write_json(folder / "job.json", row)
    lease = Lease(manager.root / "execution.lease")
    assert lease.acquire() and execution_busy(manager.root)
    monkeypatch.setattr(manager, "command", lambda folder: pytest.fail("live worker duplicated"))
    manager.tick()
    assert manager.read(row["id"])["status"] == "running"
    manager.cancel(row["id"])
    assert read_json(folder / "stop.json")["status"] == "cancelled"
    lease.close()
    manager.tick()
    assert manager.read(row["id"])["status"] == "interrupted"
    manager.resume(row["id"], acknowledge=os.name != "nt")
    assert not (folder / "stop.json").exists()


def test_store_has_only_one_manager(manager):
    with pytest.raises(ValueError, match="already_running"):
        Manager(manager.root, Config())


def test_failed_server_start_does_not_cancel_saved_workers(tmp_path):
    manager = Manager(tmp_path / "unstarted", Config(), autostart=False)
    row = add_job(manager)
    row["status"] = "running"
    folder = job_folder(manager.root, row["id"])
    write_json(folder / "job.json", row)
    manager.close(stop_workers=False)
    assert not (folder / "stop.json").exists()
    assert manager.read(row["id"])["status"] == "running"


def test_recovery_rejects_changed_input_and_failed_validation(manager, stub_pipeline):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    (folder / "input.video").write_bytes(b"changed")
    ui_worker.main(folder)
    assert manager.read(row["id"])["status"] == "failed"
    row = manager.read(row["id"])
    row["pipeline"] = {"validation": "failed"}
    write_json(folder / "job.json", row)
    with pytest.raises(ValueError, match="validation_requires_review"):
        manager.resume(row["id"])


def test_cancel_queued_job_and_recover(manager):
    row = add_job(manager)
    manager.cancel(row["id"])
    assert manager.read(row["id"])["status"] == "cancelled"
    manager.resume(row["id"], acknowledge=os.name != "nt")
    assert manager.read(row["id"])["status"] == "queued"


def test_public_projection_never_exposes_private_config(manager):
    row = add_job(manager, name='<img src=x onerror="alert(1)">.mp4')
    value = public_job(row, manager.root)
    assert "config" not in value and "attempt" not in value and "input_sha256" not in value
    assert value["name"] == row["name"]
    assert not value["can_export"]


def test_cancelled_job_status_does_not_follow_another_worker(manager):
    row = add_job(manager)
    manager.cancel(row["id"])
    row = manager.read(row["id"])
    write_json(job_folder(manager.root, row["id"]) / "stop.json", {"status": "cancelled"})
    lease = Lease(manager.root / "execution.lease")
    assert lease.acquire()
    try:
        write_json(manager.root / "worker-owner.json", {"id": "another-job"})
        assert public_job(row, manager.root)["status"] == "cancelled"
        write_json(manager.root / "worker-owner.json", {"id": row["id"]})
        assert public_job(row, manager.root)["status"] == "cancelling"
        with pytest.raises(ValueError, match="worker_still_stopping"):
            manager.resume(row["id"])
    finally:
        lease.close()


@pytest.fixture
def http_server(manager):
    server = Server(("127.0.0.1", 0), manager)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        value = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return value
    yield server, request
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_http_upload_guards_session_and_video_ranges(http_server, manager):
    server, request = http_server
    code, headers, page = request("GET", "/")
    assert code == 200 and b"Keep the useful parts" in page
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    code, _, body = request("GET", "/api/session")
    token = json.loads(body)["token"]
    for headers in ({}, {"X-Reel-Token":token,"Origin":"https://evil.example"}, {"X-Reel-Token":token,"Host":"evil.example"}, {"X-Reel-Token":token,"Sec-Fetch-Site":"cross-site"}):
        assert request("POST", "/api/jobs?name=fixture.mp4", b"video", headers)[0] == 403
    headers = {"X-Reel-Token":token,"Content-Type":"application/octet-stream","Origin":server.origin}
    code, _, body = request("POST", "/api/jobs?name=..%2Ffixture.webm", b"0123456789", headers)
    assert code == 201
    row = json.loads(body)
    assert row["name"] == "fixture.webm"
    assert manager.read(row["id"])["input_sha256"] == hashlib.sha256(b"0123456789").hexdigest()
    assert request("GET", f"/api/jobs/{row['id']}/markdown")[0] == 400
    code, response_headers, body = request("GET", f"/api/jobs/{row['id']}/video", headers={"Range":"bytes=2-4"})
    assert code == 206 and body == b"234" and response_headers["Content-Type"] == "video/webm"
    assert response_headers["Content-Range"] == "bytes 2-4/10"
    assert request("GET", f"/api/jobs/{row['id']}/video", headers={"Range":"bytes=20-30"})[0] == 416
    assert request("GET", "/api/jobs/../../pyproject.toml")[0] == 404
    assert request("POST", "/api/jobs?name=bad.html", b"bad", headers)[0] == 400
    assert request("POST", "/api/jobs?name=big.mp4", b"", {**headers,"Content-Length":str(LIMIT+1)})[0] == 400


def test_listening_port_cannot_be_shared(http_server, manager):
    server, _ = http_server
    with pytest.raises(OSError):
        Server(("127.0.0.1", server.server_port), manager)


def test_http_real_result_export_and_corruption_guard(http_server, manager, stub_pipeline):
    server, request = http_server
    row = add_job(manager)
    ui_worker.main(job_folder(manager.root, row["id"]))
    code, headers, body = request("GET", f"/api/jobs/{row['id']}/markdown")
    assert code == 200 and "attachment" in headers["Content-Disposition"]
    assert body.decode() == result(manager.root, manager.read(row["id"]))["markdown"]
    code, _, body = request("GET", f"/api/jobs/{row['id']}/result")
    assert code == 200 and json.loads(body)["review_status"] == "unreviewed"
    attempt = attempt_path(manager.root, manager.read(row["id"]))
    write_text(attempt / "notes.md", "modified")
    assert request("GET", f"/api/jobs/{row['id']}/markdown")[0] == 400
    frame = attempt.parent.parent / "frames/frame.png"
    frame.write_bytes(b"tampered")
    assert request("GET", f"/api/jobs/{row['id']}/frames/0")[0] == 400
    (job_folder(manager.root, row["id"]) / "input.video").write_bytes(b"tampered video")
    assert request("GET", f"/api/jobs/{row['id']}/video")[0] == 400


def test_progress_callback_persists_before_each_stage(tmp_path, stub_pipeline):
    path = tmp_path / "input.mp4"
    path.write_bytes(b"fixture")
    snapshots = []
    def progress(attempt, record):
        assert read_json(attempt / "run.json") == record
        snapshots.append(record)
    attempt, record = run_video(path, tmp_path / "pipeline", on_progress=progress)
    assert record["validation"] == "passed"
    assert any(r.get("current_stage") == "ocr" for r in snapshots)
    assert any(r["state"] == "synthesizing" for r in snapshots)
    assert snapshots[-1]["validation"] == "passed"


def test_progress_error_still_releases_pipeline_lock(tmp_path, stub_pipeline):
    path = tmp_path / "input.mp4"
    path.write_bytes(b"fixture")
    def fail(*args):
        raise OSError("synthetic disk failure")
    with pytest.raises(OSError):
        run_video(path, tmp_path / "pipeline", on_progress=fail)
    assert not list((tmp_path / "pipeline").rglob("active.lock"))


def wait_for(check, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return
        time.sleep(.05)
    raise AssertionError("Timed out waiting for fixture worker")


def test_cancellation_stops_owned_worker_and_child(manager, tmp_path):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    helper = tmp_path / "slow_worker.py"
    helper.write_text('''import subprocess,sys,time
from pathlib import Path
from reel_to_md import ui_worker
def slow(*args, **kwargs):
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)'])
    Path(sys.argv[1],'child.pid').write_text(str(child.pid))
    time.sleep(120)
ui_worker.versions=lambda c:{'source_sha256':'synthetic'}
ui_worker.run_video=slow
ui_worker.main(sys.argv[1])
''', encoding="utf-8")
    manager.command = lambda folder: [sys.executable, str(helper), str(folder)]
    manager.tick()
    process = manager.process
    try:
        wait_for(lambda: (folder / "child.pid").exists())
        child_pid = int((folder / "child.pid").read_text())
        manager.cancel(row["id"])
        wait_for(lambda: process.poll() is not None)
        assert manager.read(row["id"])["status"] == "cancelled"
        assert not execution_busy(manager.root)
        if os.name == "nt":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, child_pid)
            if handle:
                code = ctypes.c_ulong()
                ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
                ctypes.windll.kernel32.CloseHandle(handle)
                assert code.value != 259  # STILL_ACTIVE
        else:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                pass
            else:
                # Linux can retain a terminated child as a zombie briefly.
                stat = Path(f"/proc/{child_pid}/stat")
                assert stat.exists() and stat.read_text().split()[2] == "Z"
    finally:
        if process.poll() is None:
            manager.cancel(row["id"])
            process.wait(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows process-containment contract")
@pytest.mark.parametrize("failure", ["worker_crash", "corrupt_stop", "taskkill_failure"])
def test_windows_worker_death_contains_child_writers(manager, tmp_path, failure):
    row = add_job(manager)
    folder = job_folder(manager.root, row["id"])
    helper = tmp_path / "crash_worker.py"
    child = tmp_path / "writer.py"
    child.write_text("import sys,time\nfrom pathlib import Path\np=Path(sys.argv[1])\nwhile True:\n with p.open('ab') as f:f.write(b'x')\n time.sleep(.02)\n", encoding="utf-8")
    helper.write_text("""import subprocess,sys,time
from pathlib import Path
from reel_to_md import ui_worker
folder=Path(sys.argv[1])
def slow(*args, **kwargs):
    subprocess.Popen([sys.executable,sys.argv[2],str(folder/'heartbeat')])
    time.sleep(120)
ui_worker.versions=lambda c:{'source_sha256':'synthetic'}
ui_worker.run_video=slow
if sys.argv[3]=='taskkill_failure':
    def fail(*args,**kwargs):raise subprocess.TimeoutExpired('synthetic taskkill',8)
    ui_worker.subprocess.run=fail
ui_worker.main(folder)
""", encoding="utf-8")
    manager.command = lambda folder: [sys.executable, str(helper), str(folder), str(child), failure]
    manager.tick()
    process = manager.process
    try:
        wait_for(lambda: (folder / "heartbeat").exists())
        if failure == "worker_crash":
            process.kill()  # Actual owned process handle, never a persisted PID.
        elif failure == "corrupt_stop":
            (folder / "stop.json").write_text("{malformed", encoding="utf-8")
        else:
            manager.cancel(row["id"])
        wait_for(lambda: process.poll() is not None and not execution_busy(manager.root))
        size = (folder / "heartbeat").stat().st_size
        time.sleep(.15)
        assert (folder / "heartbeat").stat().st_size == size
        manager.tick()
        assert manager.read(row["id"])["status"] in {"interrupted", "cancelled"}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows orphan-worker containment")
def test_real_server_crash_reconnects_to_live_worker(tmp_path):
    root = tmp_path / "orphan-store"
    helper = tmp_path / "orphan-worker.py"
    helper.write_text("""import sys,time
from pathlib import Path
from reel_to_md import ui_worker
folder=Path(sys.argv[1])
ui_worker.versions=lambda c:{'source_sha256':'synthetic'}
def slow(*args,**kwargs):
    (folder/'worker-ready').write_text('ready')
    time.sleep(120)
ui_worker.run_video=slow
ui_worker.main(folder)
""", encoding="utf-8")
    coordinator = tmp_path / "coordinator.py"
    coordinator.write_text("""import sys,time,uuid
from pathlib import Path
from reel_to_md.ui_jobs import Manager,job_folder
from reel_to_md.pipeline import Config
from reel_to_md.storage import file_hash,write_json
root=Path(sys.argv[1])
m=Manager(root,Config(input_kind='synthetic_fixture'),command=lambda f:[sys.executable,sys.argv[2],str(f)])
f=job_folder(root,uuid.uuid4().hex);f.mkdir(parents=True)
(f/'input.video').write_bytes(b'synthetic')
r=m.add(f,'orphan-fixture.mp4',file_hash(f/'input.video'))
write_json(root/'fixture-id.json',{'id':r['id']})
while True:time.sleep(.2)
""", encoding="utf-8")
    server = subprocess.Popen([sys.executable, str(coordinator), str(root), str(helper)],
                              creationflags=subprocess.CREATE_NO_WINDOW)
    replacement = None
    try:
        wait_for(lambda: (root / 'fixture-id.json').exists())
        job_id = read_json(root / 'fixture-id.json')['id']
        folder = job_folder(root, job_id)
        wait_for(lambda: (folder / 'worker-ready').exists())
        server.kill(); server.wait(timeout=10)
        assert execution_busy(root)
        replacement = Manager(root, Config(input_kind='synthetic_fixture'), command=lambda f:pytest.fail('orphan duplicated'))
        replacement.stop_event.set();replacement.thread.join(timeout=2)
        replacement.tick()
        assert replacement.read(job_id)['status']=='running'
        replacement.cancel(job_id)
        wait_for(lambda:not execution_busy(root))
        assert replacement.read(job_id)['status']=='cancelled'
    finally:
        if replacement:replacement.close()
        if server.poll() is None:server.kill();server.wait(timeout=10)


def test_bound_excerpt_download_revalidates_text_even_with_matching_markdown(manager,stub_pipeline):
    from reel_to_md.generation import DRAFT_TITLE,REVIEW_NOTE,SELECTION_NOTE,required_unknowns
    row=add_job(manager);ui_worker.main(job_folder(manager.root,row["id"]))
    row=manager.read(row["id"]);attempt=attempt_path(manager.root,row)
    packet=read_json(attempt/"evidence.json");e=packet["evidence"][0]
    target={"schema_version":"1.0","title":DRAFT_TITLE,"status":"partial","claims":[{"id":"excerpt-"+e["id"]+"-0","text":e["text"],"attribution":"screen_extraction","evidence_ids":[e["id"]]}],"steps":[],"conflicts":[],"unknowns":required_unknowns(packet)+[REVIEW_NOTE],"omissions":[SELECTION_NOTE]}
    row["pipeline"]["draft_mode"]="bound_excerpts_v1"
    write_json(attempt/"first-pass-target.json",target);write_text(attempt/"notes.md",render_markdown(packet,target))
    assert result(manager.root,row)["draft_mode"]=="bound_excerpts_v1"
    target["claims"][0]["text"]="The video proves successful execution."
    write_json(attempt/"first-pass-target.json",target);write_text(attempt/"notes.md",render_markdown(packet,target))
    with pytest.raises(ValueError,match="automatic_excerpt_binding_failed"):
        result(manager.root,row)
