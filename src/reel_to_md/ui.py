"""Single-user loopback UI. No hosted assets, external APIs, or upload service."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import secrets
import socket
from urllib.parse import parse_qs, urlsplit
import uuid

from .contracts import render_markdown, validate_evidence, validate_target
from .generation import validate_generation
from .pipeline import Config
from .storage import file_hash, read_json
from .ui_jobs import ACTIVE, Manager, owns_execution, job_folder

LIMIT = 100 * 1024 * 1024
WEB = files("reel_to_md").joinpath("web")


def public_job(row, root):
    record = row.get("pipeline") or {}
    request = job_folder(root, row["id"]) / "stop.json"
    status = "cancelling" if row["status"] in ACTIVE and request.exists() else row["status"]
    if row["status"] in {"cancelled", "interrupted"} and request.exists() and owns_execution(root, row["id"]):
        status = "cancelling"
    return {"id": row["id"], "name": row["name"], "status": status,
            "message": row["message"], "created_utc": row["created_utc"], "updated_utc": row["updated_utc"],
            "started_utc": record.get("started_utc"), "stage": record.get("current_stage"),
            "stages": record.get("stages", []), "validation": record.get("validation", "not_run"),
            "can_export": record.get("validation") == "passed" and row["status"] in {"complete", "partial"},
            "can_resume": status in {"cancelled", "interrupted", "failed", "needs_attention"} and record.get("validation") != "failed",
            "attempt_count": len(row["attempts"])}


def attempt_path(root, row):
    relative = row.get("attempt")
    if not relative:
        raise ValueError("no_evidence_yet")
    attempt = (root / relative).resolve()
    if not attempt.is_relative_to((root / "pipeline").resolve()):
        raise ValueError("unsafe_attempt")
    return attempt


def result(root, row):
    attempt = attempt_path(root, row)
    evidence = read_json(attempt / "evidence.json")
    validate_evidence(evidence)
    target = None
    markdown = None
    if row["status"] in {"complete", "partial"} and (row.get("pipeline") or {}).get("validation") == "passed":
        target = read_json(attempt / "first-pass-target.json")
        validate_target(evidence, target)
        if (row.get("pipeline") or {}).get("draft_mode") == "bound_excerpts_v1":
            validate_generation(evidence, target)
        markdown = (attempt / "notes.md").read_text(encoding="utf-8")
        if markdown != render_markdown(evidence, target):
            raise ValueError("notes_integrity_failure")
    selected = read_json(attempt / "frames.json")
    return {"evidence": evidence, "target": target, "markdown": markdown,
            "frames": [{"index": i, "seconds": frame["seconds"]} for i, frame in enumerate(selected["frames"])],
            "review_status": "unreviewed", "draft_mode": (row.get("pipeline") or {}).get("draft_mode")}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address, manager):
        if address[0] != "127.0.0.1":
            raise ValueError("ui_requires_literal_loopback")
        self.manager = manager
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, *args):
        pass  # Source filenames and URL arguments stay out of routine logs.

    def reply(self, code, body, kind="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.headers_safe()
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def headers_safe(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def guard(self, mutation=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            raise PermissionError("host_blocked")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise PermissionError("cross_site_blocked")
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            raise PermissionError("origin_blocked")
        if mutation and not secrets.compare_digest(self.headers.get("X-Reel-Token", ""), self.server.token):
            raise PermissionError("local_session_required")

    def dispatch(self, mutation=False):
        try:
            self.guard(mutation)
            if mutation:
                self.post()
            else:
                self.get()
        except PermissionError:
            self.close_connection = True
            self.reply(403, {"error": "This request is not from the local app session."})
        except (ValueError, KeyError, FileNotFoundError, IndexError, TypeError) as exc:
            self.close_connection = True
            message = str(exc) if type(exc) is ValueError and str(exc) in {"video_size_limit", "worker_still_stopping", "interrupted_processes_require_acknowledgment", "job_is_not_recoverable", "draft_failed_validation_requires_review_or_new_configuration", "job_is_not_active"} else "The requested job or result is not available."
            self.reply(400, {"error": message})
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            self.close_connection = True
        except OSError:
            self.close_connection = True
            self.reply(500, {"error": "Local storage is unavailable. Saved work is retained."})

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch(True)

    def get(self):
        path = urlsplit(self.path).path
        if path in {"/", "/app.js", "/style.css"}:
            name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[path]
            kind = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8"}[path]
            return self.reply(200, WEB.joinpath(name).read_bytes(), kind)
        manager = self.server.manager
        if path == "/api/session":
            c = manager.config
            return self.reply(200, {"token": self.server.token, "mode": "Local model synthesis" if c.text_model else "Extractive draft", "text_model": c.text_model, "vision_model": c.vision_model, "asr": bool(c.asr_model), "ocr": True, "max_bytes": LIMIT})
        if path == "/api/jobs":
            return self.reply(200, [public_job(row, manager.root) for row in manager.rows()])
        match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})(?:/(result|video|markdown|frames/([0-9]+)))?", path)
        if not match:
            return self.reply(404, {"error": "Not found."})
        job_id, action, index = match.groups()
        row = manager.read(job_id)
        if action is None:
            return self.reply(200, public_job(row, manager.root))
        if action == "video":
            kind = {".mov": "video/quicktime", ".webm": "video/webm", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo"}.get(Path(row["name"]).suffix.lower(), "video/mp4")
            video = job_folder(manager.root, job_id) / "input.video"
            if file_hash(video) != row["input_sha256"]:
                raise ValueError("video_integrity_failure")
            return self.send_file(video, kind)
        if action in {"result", "markdown"}:
            value = result(manager.root, row)
            if action == "result":
                return self.reply(200, value)
            if value["markdown"] is None:
                raise ValueError("no_valid_export")
            return self.reply(200, value["markdown"], "text/markdown; charset=utf-8", {"Content-Disposition": 'attachment; filename="notes.md"'})
        attempt = attempt_path(manager.root, row)
        frame = read_json(attempt / "frames.json")["frames"][int(index)]
        frame_path = (attempt.parent.parent / "frames" / frame["file"]).resolve()
        if frame_path.parent != (attempt.parent.parent / "frames").resolve() or file_hash(frame_path) != frame["sha256"]:
            raise ValueError("frame_integrity_failure")
        return self.send_file(frame_path, "image/png")

    def send_file(self, path, kind):
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        header = self.headers.get("Range")
        if header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
            if not match or not any(match.groups()):
                return self.reply(416, b"", extra={"Content-Range": f"bytes */{size}"})
            first, last = match.groups()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if start > end or start >= size:
                return self.reply(416, b"", extra={"Content-Range": f"bytes */{size}"})
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.headers_safe()
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def content_length(self, maximum):
        raw = self.headers.get_all("Content-Length", [])
        if len(raw) != 1 or not re.fullmatch(r"[0-9]+", raw[0]) or self.headers.get("Transfer-Encoding"):
            raise ValueError("invalid_content_length")
        length = int(raw[0])
        if not 0 < length <= maximum:
            raise ValueError("video_size_limit")
        return length

    def post(self):
        parts = urlsplit(self.path)
        manager = self.server.manager
        if parts.path == "/api/jobs":
            length = self.content_length(LIMIT)
            if self.headers.get("Content-Type") != "application/octet-stream":
                raise ValueError("upload_type_invalid")
            name = parse_qs(parts.query).get("name", ["video.mp4"])[0]
            name = name.replace("\\", "/").split("/")[-1][:200]
            suffix = Path(name).suffix.lower()
            if suffix not in {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}:
                raise ValueError("unsupported_video_extension")
            folder = job_folder(manager.root, uuid.uuid4().hex)
            folder.mkdir(parents=True)
            temp = folder / "upload.part"
            try:
                sha = hashlib.sha256()
                with temp.open("xb") as stream:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("upload_incomplete")
                        stream.write(chunk)
                        sha.update(chunk)
                        remaining -= len(chunk)
                temp.rename(folder / "input.video")
                row = manager.add(folder, name, sha.hexdigest())
                return self.reply(201, public_job(row, manager.root))
            finally:
                temp.unlink(missing_ok=True)
        match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})/(cancel|resume)", parts.path)
        if not match:
            return self.reply(404, {"error": "Not found."})
        length = self.content_length(4096)
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("invalid_request")
        job_id, action = match.groups()
        if action == "cancel":
            manager.cancel(job_id)
        else:
            acknowledged = data.get("acknowledge_model_retry", False)
            if type(acknowledged) is not bool:
                raise ValueError("invalid_acknowledgment")
            manager.resume(job_id, acknowledged)
        return self.reply(200, public_job(manager.read(job_id), manager.root))


def serve(root, config=Config(), port=8791):
    manager = Manager(root, config, autostart=False)
    server = None
    try:
        server = Server(("127.0.0.1", port), manager)
        manager.start()
        print(f"Reel to MD: {server.origin}", flush=True)
        print("Local only. Keep this terminal running; press Ctrl+C to stop.", flush=True)
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
        manager.close(stop_workers=server is not None)
