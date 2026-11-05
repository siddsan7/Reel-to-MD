"""Generate source-controlled facts as synthetic media; run live models then cache replay.

Requires FFmpeg's flite filter. Never downloads models or reads real source media.
"""
from dataclasses import replace
import argparse
import json
import re
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from reel_to_md.pipeline import Config, run_video
from reel_to_md.storage import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def command(args):
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, timeout=60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?", type=Path, default=ROOT / "data/private/local-config.json")
    parser.add_argument("--require-ocr", action="store_true", help="Require available OCR and an exact timestamped command in the synthetic frame")
    args = parser.parse_args()
    folder = ROOT / "work/local-smoke"
    folder.mkdir(parents=True, exist_ok=True)
    text = "Set the maximum number of retries to three. Then run the Python script. Successful execution is unknown."
    (folder / "speech.txt").write_text(text, encoding="utf-8")
    image = Image.new("RGB", (960, 540), "white")
    font_path = next((p for p in (Path("C:/Windows/Fonts/consola.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")) if p.exists()), None)
    font = ImageFont.truetype(str(font_path), 38) if font_path else ImageFont.load_default(size=38)
    ImageDraw.Draw(image).multiline_text((45, 80), "SYNTHETIC TUTORIAL\n\nmax_retries = 3\npython agent.py\n\nExecution status: unknown", fill="black", font=font, spacing=14)
    image.save(folder / "screen.png")
    command(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "flite=textfile=work/local-smoke/speech.txt:voice=slt", "-ar", "16000", "-ac", "1", "-y", str(folder / "speech.wav")])
    command(["ffmpeg", "-nostdin", "-v", "error", "-loop", "1", "-i", str(folder / "screen.png"), "-i", str(folder / "speech.wav"), "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "-y", str(folder / "tutorial.mp4")])
    config = replace(Config(**read_json(args.config)), input_kind="synthetic_fixture")
    results = []
    for name in ("first", "repeat"):
        directory, record = run_video(folder / "tutorial.mp4", ROOT / "outputs/local-smoke", config)
        summary = {"attempt": name, "directory": str(directory), "state": record["state"], "validation": record["validation"], "seconds": record["latency_seconds"], "input_tokens": record["input_tokens"], "output_tokens": record["output_tokens"], "stages": record["stages"], "cost_usd": record["cost_usd"]}
        if (directory / "evidence.json").is_file():
            packet = read_json(directory / "evidence.json")
            summary["channels"] = packet["channels"]
            summary["asr_contains_retry_value"] = any(re.search(r"\b(?:three|3)\b", e["text"].lower()) for e in packet["evidence"] if e["kind"] == "transcript")
            summary["vision_contains_command"] = any("python agent.py" in e["text"] for e in packet["evidence"] if e["kind"] == "visual_description")
            summary["ocr_contains_command"] = any("python agent.py" in e["text"].splitlines() for e in packet["evidence"] if e["kind"] == "ocr")
        results.append(summary)
        print(json.dumps(summary), flush=True)
        if record["state"] == "failed":
            break
    write_json(ROOT / "outputs/local-smoke-summary.json", {"synthetic": True, "expected_speech": text, "results": results})
    passed = (
        len(results) == 2
        and all(r["validation"] == "passed" and r.get("channels", {}).get("audio") == "available" and r.get("channels", {}).get("vision") == "available" and r.get("asr_contains_retry_value") and r.get("vision_contains_command") for r in results)
        and results[-1]["input_tokens"] == results[-1]["output_tokens"] == 0
        and all(s["cache_hit"] for s in results[-1]["stages"] if s["status"] == "success")
        and (not args.require_ocr or all(r.get("channels", {}).get("ocr") == "available" and r.get("ocr_contains_command") for r in results))
    )
    if not passed:
        sys.exit(1)
