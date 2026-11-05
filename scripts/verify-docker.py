"""Independent artifact checks for container runs; do not normalize OCR strings."""
import argparse
from pathlib import Path
import re

from reel_to_md.contracts import validate_target
from reel_to_md.storage import read_json, write_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path)
parser.add_argument("mode", choices=["extract", "models"])
args = parser.parse_args()
attempts = sorted(args.directory.joinpath(args.mode).rglob("run.json"), key=lambda p: read_json(p)["started_utc"])
if len(attempts) != (1 if args.mode == "extract" else 2):
    raise SystemExit("Unexpected attempt count; refusing to accept stale or missing results")
rows = []
for index, path in enumerate(attempts):
    record = read_json(path)
    packet = read_json(path.parent / "evidence.json")
    target = read_json(path.parent / "first-pass-target.json")
    validate_target(packet, target)
    assert record["validation"] == "passed" and (path.parent / "notes.md").is_file()
    required = ("audio", "ocr", "vision") if args.mode == "models" else ("audio", "ocr")
    assert all(packet["channels"][name] == "available" for name in required), packet["channels"]
    assert record["result_kind"] == "synthetic_video_wiring"
    assert any(re.search(r"\b(?:3|three)\b", e["text"].lower()) for e in packet["evidence"] if e["kind"] == "transcript")
    exact = any("python agent.py" in e["text"].splitlines() for e in packet["evidence"] if e["kind"] == "ocr")
    if args.mode == "models":
        assert any("python agent.py" in e["text"] for e in packet["evidence"] if e["kind"] == "visual_description")
    if index == 1:
        assert record["job_id"] == rows[0]["job_id"]
        assert record["input_tokens"] == record["output_tokens"] == 0
        assert all(s["status"] == "success" and s["cache_hit"] for s in record["stages"])
    rows.append({"job_id": record["job_id"], "attempt_id": record["attempt_id"], "validation": record["validation"], "channels": packet["channels"], "seconds": record["latency_seconds"], "input_tokens": record["input_tokens"], "output_tokens": record["output_tokens"], "ocr_version": record["versions"]["tesseract"], "ocr_exact_command": exact, "ocr_text": [e["text"] for e in packet["evidence"] if e["kind"] == "ocr"]})
result = {"synthetic": True, "structural_checks_passed": True, "ocr_fidelity_passed": all(row["ocr_exact_command"] for row in rows), "attempts": rows}
write_json(args.directory / (args.mode + "-report.json"), result)
print(f"{args.mode}: structural checks passed; OCR exact-command fidelity: {result['ocr_fidelity_passed']}")
if not result["ocr_fidelity_passed"]:
    print("OCR source fidelity failed. Original uncertain text is retained without normalization.")
    raise SystemExit(1)
