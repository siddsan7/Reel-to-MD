"""Local CLI; synthetic wiring checks are explicitly separate from video jobs."""
import argparse
from pathlib import Path
import sys
import time
import uuid

from . import __version__
from .contracts import render_markdown, validate_evidence, validate_target
from .pipeline import Config, run_video
from .storage import read_json, write_json, write_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline local-video evidence pipeline; no hosted inference.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="action", required=True)
    example = commands.add_parser("check-example", help="Validate/render a labeled synthetic input/target pair")
    example.add_argument("example", type=Path)
    example.add_argument("--output", type=Path, default=Path("outputs/synthetic-check"))
    run = commands.add_parser("run", help="Process a local video into a private job directory")
    run.add_argument("video", type=Path)
    run.add_argument("--output", type=Path, default=Path("outputs/jobs"))
    run.add_argument("--config", type=Path, help="JSON Config fields; local-only models")
    args = parser.parse_args(argv)
    try:
        if args.action == "check-example":
            start = time.monotonic()
            value = read_json(args.example)
            if value.get("metadata", {}).get("synthetic") is not True:
                raise ValueError("check-example_requires_synthetic_label")
            validate_evidence(value["input"])
            validate_target(value["input"], value["target"])
            write_text(args.output / "notes.md", "SYNTHETIC WIRING CHECK — not real-video validation.\n\n" + render_markdown(value["input"], value["target"]))
            write_json(args.output / "run.json", {"pipeline_version": __version__, "result_kind": "synthetic_wiring_only", "validation": "passed", "latency_seconds": time.monotonic() - start, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "paid_cash_usd": 0})
            print(f"Synthetic wiring check passed: {args.output.resolve()}")
            return 0
        config = Config(**read_json(args.config)) if args.config else Config()
        directory, record = run_video(args.video, args.output, config)
        print(f"{record['state']}: {directory.resolve()}")
        return 1 if record["state"] == "failed" else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        detail = "check input and configuration"
        print(f"Failed ({type(exc).__name__}): {detail}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
