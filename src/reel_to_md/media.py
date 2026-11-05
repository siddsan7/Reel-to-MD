"""Bounded local decoding. Never accepts media URLs or invokes a shell."""
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageStat

from .contracts import redact_text
from .storage import file_hash


def command(args, timeout=60):
    result = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError("decoder_or_extractor_failed")
    return result.stdout


def tesseract_command():
    """Find standard Windows installs without changing the user's global PATH."""
    override = os.environ.get("TESSERACT_CMD")
    if override:
        return override
    found = shutil.which("tesseract")
    if found:
        return found
    for variable, suffix in (("LOCALAPPDATA", "Programs/Tesseract-OCR/tesseract.exe"), ("LOCALAPPDATA", "Tesseract-OCR/tesseract.exe"), ("ProgramFiles", "Tesseract-OCR/tesseract.exe"), ("ProgramFiles(x86)", "Tesseract-OCR/tesseract.exe")):
        root = os.environ.get(variable)
        if root and (path := Path(root) / suffix).is_file():
            return str(path)
    return "tesseract"  # Preserve an explicit missing-executable channel failure.


def tool_version(executable):
    try:
        resolved = tesseract_command() if executable == "tesseract" else executable
        flag = "--version" if executable == "tesseract" else "-version"
        return command([resolved, flag], timeout=10).decode(errors="replace").splitlines()[0]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "unavailable"


def probe(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("media_size_limit")
    raw = command(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-show_format", "-show_streams", "-of", "json", str(path)], 20)
    info = json.loads(raw)
    duration = float(info.get("format", {}).get("duration", 0))
    video = next((x for x in info["streams"] if x["codec_type"] == "video"), None)
    if not math.isfinite(duration) or not 0 < duration <= 120 or not video:
        raise ValueError("media_duration_or_video_invalid")
    if video.get("width", 0) * video.get("height", 0) > 3840 * 2160:
        raise ValueError("media_resolution_limit")
    return {"duration": duration, "has_audio": any(x["codec_type"] == "audio" for x in info["streams"])}


def frames(path, directory, duration, interval=2.0, cap=60, difference=2.0):
    """Uniform samples with conservative thumbnail dedup; keep original PNGs."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    selected, previous = [], None
    count = math.ceil(duration / interval)
    for index in range(min(count, cap)):
        timestamp = index * interval
        output = directory / f"frame-{index:04}.png"
        command(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe", "-ss", str(timestamp), "-i", str(Path(path).resolve()), "-frames:v", "1", "-threads", "1", "-y", str(output)])
        with Image.open(output) as original:
            thumb = original.convert("L").resize((64, 64))
        if previous is not None and ImageStat.Stat(ImageChops.difference(thumb, previous)).mean[0] < difference:
            output.unlink()
            continue
        selected.append({"file": output.name, "seconds": timestamp, "sha256": file_hash(output)})
        previous = thumb
    return {"frames": selected, "truncated": count > cap, "policy": "uniform-thumbnail-dedup-v1", "interval_seconds": interval, "cap": cap, "difference_threshold": difference}


def ocr(selected, directory):
    # Rescale pixels before recognition; never repair recognized punctuation/spaces.
    with tempfile.TemporaryDirectory(prefix="reel-ocr-") as temporary:
        return _ocr(selected, directory, Path(temporary))


def _ocr(selected, directory, temporary):
    entries = []
    previous = None
    for frame in selected:
        source = Path(directory) / frame["file"]
        with Image.open(source) as image:
            scale = max(1, min(2, 3840 / image.width, 2160 / image.height))
            prepared = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
            prepared.save(temporary / "frame.png")
        raw = command([tesseract_command(), str(temporary / "frame.png"), "stdout", "-l", "eng", "--psm", "11", "tsv"], 30).decode("utf-8", errors="replace")
        rows = list(csv.DictReader(io.StringIO(raw), delimiter="\t"))
        words = [r for r in rows if r.get("text", "").strip() and float(r["conf"]) >= 0]
        lines = {}
        for row in words:
            line_id = tuple(row.get(k) for k in ("page_num", "block_num", "par_num", "line_num"))
            lines.setdefault(line_id, []).append(row["text"].strip())
        text = redact_text("\n".join(" ".join(line) for line in lines.values()))
        if text and text != previous:
            entries.append({"start_seconds": frame["seconds"], "end_seconds": frame["seconds"], "text": text, "review_flag": "uncertain" if any(float(r["conf"]) < 80 for r in words) else "normal"})
        previous = text
    return entries


def transcribe(path, model_path):
    if not model_path or not Path(model_path).is_dir():
        raise ValueError("local_asr_model_not_configured")
    from faster_whisper import WhisperModel

    model = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
    segments, _ = model.transcribe(str(Path(path).resolve()), language="en", beam_size=5, vad_filter=True)
    return [{"start_seconds": s.start, "end_seconds": s.end, "text": redact_text(s.text.strip()), "review_flag": "normal"} for s in segments if s.text.strip()]
