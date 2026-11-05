"""Content addressing and atomic private artifacts (never routine text logs)."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def local_path(path):
    """Support deeply nested private job paths on Windows without OS policy changes."""
    path = Path(path).resolve()
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        value = str(path)
        path = Path("\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value)
    return path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_text(path, text):
    path = local_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        # Windows readers can briefly deny replacement of an open destination.
        # Retry only this local atomic commit, never extraction or model calls.
        for attempt in range(6):
            try:
                os.replace(name, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(min(0.02 * 2 ** attempt, 0.2))
    finally:
        Path(name).unlink(missing_ok=True)
