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
    ui = commands.add_parser("serve", help="Open the local upload, progress, review, and export UI")
    ui.add_argument("--config", type=Path, help="Local pipeline configuration; omitted uses extractive drafts")
    ui.add_argument("--store", type=Path, default=Path("outputs/local-ui"))
    ui.add_argument("--port", type=int, default=8791)
    review = commands.add_parser("review-init", help="Create an offline human-review page and annotations")
    review.add_argument("attempt", type=Path)
    review.add_argument("--video", type=Path, help="Original local video; required for natural-clip finalization")
    review.add_argument("--target", type=Path, help="Score a separately reviewed target instead of the original first pass")
    review.add_argument("--output", type=Path)
    finalize = commands.add_parser("review-finalize", help="Validate human annotations and export a new review revision")
    finalize.add_argument("review", type=Path, help="Completed annotation JSON beside source.json")
    finalize.add_argument("--output", type=Path)
    evaluate = commands.add_parser("evaluate", help="Aggregate finalized human reviews without model calls")
    evaluate.add_argument("reviews", type=Path, nargs="+")
    evaluate.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "serve":
            from .ui import serve
            serve(args.store, Config(**read_json(args.config)) if args.config else Config(), args.port)
            return 0
        if args.action in {"review-init", "review-finalize", "evaluate"}:
            from .review import initialize, finalize as finalize_review, evaluate as evaluate_reviews
            output = args.output or Path("outputs") / ("evaluations" if args.action == "evaluate" else "reviews") / uuid.uuid4().hex
            if args.action == "review-init":
                directory = initialize(args.attempt, output, video=args.video, target=args.target)
            elif args.action == "review-finalize":
                directory = finalize_review(args.review, output)
            else:
                directory = evaluate_reviews(args.reviews, output)
            print(f"{args.action}: {directory}")
            return 0
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
        # Review validation messages contain field names, never source content.
        detail = str(exc) if args.action in {"review-init", "review-finalize", "evaluate"} and type(exc) is ValueError else "check input and configuration"
        print(f"Failed ({type(exc).__name__}): {detail}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
