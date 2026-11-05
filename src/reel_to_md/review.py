"""Local human review snapshots, immutable finalizations, and development scoring."""
from datetime import datetime, timezone
import math
from pathlib import Path
import shutil
import tempfile
import uuid

from jsonschema import Draft202012Validator

from .contracts import _validate_schema, render_markdown, validate_evidence, validate_target
from .evaluation import aggregate, score
from .storage import digest, file_hash, local_path, read_json, write_json, write_text


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string", "maxLength": 100000}
LABEL = {"type": "string", "minLength": 1, "maxLength": 200}
BOOL = {"type": "boolean"}
PENDING_BOOL = {"type": ["boolean", "null"]}


def array(item):
    return {"type": "array", "items": item, "maxItems": 1000}


IDS = {**array(LABEL), "uniqueItems": True}
ISSUE = obj({"id": LABEL, "text": LABEL, "represented": PENDING_BOOL, "output_paths": IDS})
REVIEW_SCHEMA = obj({
    "schema_version": {"const": "1.0"}, "review_id": LABEL, "source_digest": LABEL,
    "reviewer": TEXT, "clip_key": TEXT, "source_group": TEXT, "condition": TEXT,
    "split": {"enum": ["development", "challenge"]},
    "source_reviewed": BOOL, "source_matches_attempt": BOOL,
    "unit_coverage_confirmed": BOOL, "reference_inventory_complete": BOOL,
    "review_minutes": {"type": "number", "minimum": 0},
    "decision": {"enum": ["pending", "accept", "edit", "reject"]}, "notes": TEXT,
    "units": array(obj({"id": LABEL, "path": LABEL, "text": {**TEXT, "minLength": 1},
                        "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1}, "factual": PENDING_BOOL,
                        "exclusion_reason": TEXT, "input_support": {"enum": [None, "full", "partial", "none"]},
                        "source_consistent": PENDING_BOOL,
                        # Preserve malformed original IDs verbatim for rejection/scoring.
                        "citations": array(obj({"evidence_id": {}, "supports": PENDING_BOOL}))})),
    "facts": array(obj({"id": LABEL, "text": LABEL, "important": BOOL,
                        "source_supported": BOOL, "input_available": BOOL, "recovered_by": IDS,
                        "technical_value": {"type": ["string", "null"], "minLength": 1},
                        "incorrectly_unknown": PENDING_BOOL})),
    "conflicts": array(ISSUE), "gaps": array(ISSUE),
    "corrected_target": {"type": ["object", "null"]},
})


def candidates(target):
    """Every output text field is presented for factual/atomic human judgment."""
    rows = []
    if not isinstance(target, dict):
        return rows
    if isinstance(target.get("title"), str) and target["title"].strip():
        rows.append({"path": "/title", "text": target["title"], "evidence_ids": []})
    for name in ("claims", "steps", "conflicts", "unknowns", "omissions"):
        items = target.get(name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            refs = item.get("evidence_ids", [])
            refs = refs if isinstance(refs, list) else []
            for field in (("text", "command") if name == "steps" else ("reason",) if name == "omissions" else ("text",)):
                value = item.get(field)
                if isinstance(value, str) and value.strip():
                    rows.append({"path": f"/{name}/{index}/{field}", "text": value, "evidence_ids": refs})
    return rows


def _originals(attempt):
    result = {}
    for name in ("evidence.json", "run.json", "first-pass-target.json", "first-pass-response.txt", "notes.md", "frames.json"):
        path = attempt / name
        if path.is_file():
            result[name] = file_hash(path)
    return result


def _classification(run):
    if run.get("input_kind") == "synthetic_fixture" or run.get("result_kind") in {"synthetic_wiring_only", "synthetic_video_wiring"}:
        return True
    if run.get("input_kind") == "local_video" or run.get("result_kind") == "local_video_unreviewed":
        return False
    return None


def _new_directory(output, build):
    output = local_path(output)
    if output.exists():
        raise ValueError("Output already exists; use a new revision directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="review-", dir=output.parent) as temp:
        folder = local_path(temp) / "result"
        folder.mkdir()
        build(folder)
        folder.rename(output)
    return output


def initialize(attempt, output, *, video=None, target=None):
    attempt = local_path(attempt)
    output = local_path(output)
    if output == attempt or attempt in output.parents or output in attempt.parents:
        raise ValueError("Review output must be separate from the original attempt")
    packet, run = read_json(attempt / "evidence.json"), read_json(attempt / "run.json")
    validate_evidence(packet)
    target_path = local_path(target) if target else attempt / "first-pass-target.json"
    candidate = read_json(target_path) if target_path.exists() else None
    validity = {"schema": False, "semantic": False}
    if candidate is not None:
        try:
            _validate_schema(candidate, "target")
            validity["schema"] = True
            validate_target(packet, candidate)
            validity["semantic"] = True
        except ValueError:
            pass
    source = {"schema_version": "1.0", "attempt": str(attempt), "original_hashes": _originals(attempt),
              "evidence": packet, "run": run, "target": candidate,
              "variant": "reviewed" if target else "first_pass",
              "target_file": str(target_path) if target_path.exists() else None,
              "target_sha256": file_hash(target_path) if target_path.exists() else None,
              "raw_response": (attempt / "first-pass-response.txt").read_text(encoding="utf-8") if (attempt / "first-pass-response.txt").exists() and not target else None,
              "synthetic": _classification(run),
              "validity": validity, "assets": [], "video": None, "video_matches_run": None,
              "candidates": candidates(candidate)}
    if video:
        video = local_path(video)
        if not video.is_file() or video.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Review video must be a local file up to 100 MiB")
        video_hash = file_hash(video)
        if run.get("input_sha256") and run["input_sha256"] != video_hash:
            raise ValueError("Video hash does not match this pipeline attempt")
        source["video_matches_run"] = True if run.get("input_sha256") else None
        source["video"] = {"original_path": str(video), "sha256": video_hash,
                           "file": "assets/source" + (video.suffix.lower() if video.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"} else ".bin")}
    review = {"schema_version": "1.0", "review_id": uuid.uuid4().hex, "source_digest": "",
              "reviewer": "", "clip_key": "", "source_group": "", "condition": "B1",
              "split": "challenge" if source["synthetic"] else "development",
              "source_reviewed": False, "source_matches_attempt": False,
              "unit_coverage_confirmed": False, "reference_inventory_complete": False,
              "review_minutes": 0, "decision": "pending", "notes": "", "facts": [], "conflicts": [], "gaps": [],
              "units": [{"id": f"u{i}", **item, "start": 0, "end": len(item["text"]), "factual": None, "exclusion_reason": "", "input_support": None,
                         "source_consistent": None, "citations": [{"evidence_id": ref, "supports": None} for ref in item["evidence_ids"]]}
                        for i, item in enumerate(source["candidates"], 1)], "corrected_target": None}
    for unit in review["units"]:
        del unit["evidence_ids"]

    def build(folder):
        (folder / "assets").mkdir()
        if video:
            shutil.copyfile(video, folder / source["video"]["file"])
            source["assets"].append({"file": source["video"]["file"], "sha256": source["video"]["sha256"]})
        frames_path = attempt / "frames.json"
        if frames_path.exists():
            frames = read_json(frames_path)["frames"]
            for index, frame in enumerate(frames):
                name = frame["file"]
                if Path(name).name != name or "/" in name or "\\" in name:
                    raise ValueError("Unsafe frame path")
                original = attempt.parent.parent / "frames" / name
                if file_hash(original) != frame["sha256"]:
                    raise ValueError("Source frame integrity mismatch")
                relative = f"assets/frame-{index:04}.png"
                shutil.copyfile(original, folder / relative)
                source["assets"].append({"file": relative, "sha256": frame["sha256"], "seconds": frame["seconds"]})
        review["source_digest"] = digest(source)
        write_json(folder / "source.json", source)
        write_json(folder / "review.json", review)
        from .review_page import render_page
        write_text(folder / "review.html", render_page(source, review))
    return _new_directory(output, build)


def validate_review(source, review):
    errors = list(Draft202012Validator(REVIEW_SCHEMA).iter_errors(review))
    if errors:
        raise ValueError("Review shape invalid at " + ".".join(map(str, errors[0].path)))
    if digest(source) != review["source_digest"]:
        raise ValueError("Source snapshot changed")
    if source["candidates"] != candidates(source["target"]) or source["synthetic"] != _classification(source["run"]):
        raise ValueError("Source snapshot has inconsistent candidates or classification")
    if source["synthetic"] is None:
        raise ValueError("Legacy attempt lacks input classification; create a new explicitly classified pipeline attempt")
    for key in ("reviewer", "clip_key", "source_group", "condition"):
        if not review[key].strip() or len(review[key]) > 200:
            raise ValueError("Review identity fields must be nonblank and at most 200 characters")
    if review["decision"] == "pending" or not math.isfinite(review["review_minutes"]):
        raise ValueError("Review decision/time incomplete")
    for key in ("source_reviewed", "source_matches_attempt", "unit_coverage_confirmed", "reference_inventory_complete"):
        if not review[key]:
            raise ValueError("Human source, completeness, and identity attestations are required")
    if not source["synthetic"] and source["video"] is None:
        raise ValueError("Natural-clip finalization requires a hashed original video")
    if source["synthetic"] and review["split"] != "challenge":
        raise ValueError("Synthetic examples must remain in the challenge cohort")
    paths = {item["path"]: item for item in source["candidates"]}
    units, covered, seen_text = {}, {}, set()
    for unit in review["units"]:
        span = (unit["path"], unit["start"], unit["end"])
        if unit["id"] in units or span in seen_text:
            raise ValueError("Duplicate atomic unit")
        units[unit["id"]] = unit
        seen_text.add(span)
        if unit["path"] not in paths or unit["start"] >= unit["end"] or unit["end"] > len(paths[unit["path"]]["text"]) or unit["text"] != paths[unit["path"]]["text"][unit["start"]:unit["end"]]:
            raise ValueError("Atomic unit must be a literal span of its original output field")
        original = paths[unit["path"]]
        covered.setdefault(unit["path"], set()).update(range(unit["start"], unit["end"]))
        if [link["evidence_id"] for link in unit["citations"]] != original["evidence_ids"]:
            raise ValueError("Citation labels must cover original links in order")
        if unit["factual"] is None:
            raise ValueError("Atomic factual status is pending")
        if unit["factual"]:
            if unit["input_support"] is None or unit["source_consistent"] is None or any(link["supports"] is None for link in unit["citations"]):
                raise ValueError("Factual unit labels are incomplete")
            known = {item["id"] for item in source["evidence"]["evidence"]}
            if any(link["supports"] and (not isinstance(link["evidence_id"], str) or link["evidence_id"] not in known) for link in unit["citations"]):
                raise ValueError("A nonexistent evidence ID cannot support a claim")
        elif not unit["exclusion_reason"].strip():
            raise ValueError("Nonfactual exclusions require a reason")
    for path, original in paths.items():
        required = {i for i, character in enumerate(original["text"]) if not character.isspace()}
        if path not in covered or not required <= covered[path]:
            raise ValueError("Atomic units omit original output text")
    for collection in ("facts", "conflicts", "gaps"):
        items = review[collection]
        if len({item["id"] for item in items}) != len(items) or len({item["text"] for item in items}) != len(items):
            raise ValueError("Duplicate reference item")
    for fact in review["facts"]:
        if any(key not in units or not units[key]["factual"] for key in fact["recovered_by"]):
            raise ValueError("Fact matches must reference factual unit IDs")
        if fact["source_supported"] and fact["input_available"] and fact["incorrectly_unknown"] is None:
            raise ValueError("Answerable fact uncertainty label is pending")
    for item in review["conflicts"] + review["gaps"]:
        if item["represented"] is None or any(path not in paths for path in item["output_paths"]):
            raise ValueError("Conflict/gap judgment incomplete or output path unknown")
        if bool(item["output_paths"]) != item["represented"]:
            raise ValueError("Represented conflicts/gaps require output references; missed ones have none")
    corrected = review["corrected_target"]
    if review["decision"] == "edit":
        if corrected is None or corrected == source["target"]:
            raise ValueError("Edit decision requires a distinct corrected target")
        validate_target(source["evidence"], corrected)
    elif corrected is not None:
        raise ValueError("Corrections require an edit decision")
    elif review["decision"] == "accept":
        validate_target(source["evidence"], source["target"])


def _check_integrity(folder, source):
    attempt = local_path(source["attempt"])
    if _originals(attempt) != source["original_hashes"]:
        raise ValueError("Original attempt artifacts changed or disappeared")
    if read_json(attempt / "evidence.json") != source["evidence"] or read_json(attempt / "run.json") != source["run"]:
        raise ValueError("Source snapshot does not match original attempt")
    if source["target_file"] and file_hash(source["target_file"]) != source["target_sha256"]:
        raise ValueError("Original target changed")
    if source["target_file"] and read_json(source["target_file"]) != source["target"]:
        raise ValueError("Source snapshot does not match original target")
    for asset in source["assets"]:
        path = local_path(folder / asset["file"])
        if local_path(folder) not in path.parents or file_hash(path) != asset["sha256"]:
            raise ValueError("Review asset integrity mismatch")


def finalize(review_file, output):
    review_file = local_path(review_file)
    if review_file.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Review annotation file exceeds 8 MiB")
    source = read_json(review_file.parent / "source.json")
    review = read_json(review_file)
    validate_review(source, review)
    _check_integrity(review_file.parent, source)
    if local_path(output) == local_path(source["attempt"]) or local_path(source["attempt"]) in local_path(output).parents:
        raise ValueError("Finalized review must be separate from original attempt")
    metrics = score(source, review)

    def build(folder):
        write_json(folder / "source.json", source)
        write_json(folder / "review.json", review)
        write_json(folder / "scores.json", metrics)
        for asset in source["assets"]:
            destination = folder / asset["file"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(review_file.parent / asset["file"], destination)
            if file_hash(destination) != asset["sha256"]:
                raise ValueError("Source asset changed during finalization")
        if review["decision"] != "reject":
            target = review["corrected_target"] if review["decision"] == "edit" else source["target"]
            write_json(folder / "reviewed-target.json", target)
            write_text(folder / "reviewed-notes.md", render_markdown(source["evidence"], target))
        names = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())
        write_json(folder / "manifest.json", {"schema_version": "1.0", "finalization_id": uuid.uuid4().hex,
                   "finalized_utc": datetime.now(timezone.utc).isoformat(), "review_id": review["review_id"],
                   "files": {name: file_hash(folder / name) for name in names}})
    return _new_directory(output, build)


def load_finalized(folder):
    folder = local_path(folder)
    manifest = read_json(folder / "manifest.json")
    required = {"source.json", "review.json", "scores.json"}
    if not required <= manifest["files"].keys():
        raise ValueError("Incomplete finalization manifest")
    for name, expected in manifest["files"].items():
        path = local_path(folder / name)
        if folder not in path.parents or file_hash(path) != expected:
            raise ValueError("Finalized review integrity mismatch")
    source, review = read_json(folder / "source.json"), read_json(folder / "review.json")
    if manifest["review_id"] != review["review_id"]:
        raise ValueError("Finalized review identity mismatch")
    validate_review(source, review)
    for asset in source["assets"]:
        if asset["file"] not in manifest["files"] or manifest["files"][asset["file"]] != asset["sha256"]:
            raise ValueError("Finalization is missing a source asset")
    metrics = score(source, review)
    if metrics != read_json(folder / "scores.json"):
        raise ValueError("Stored scores do not match original annotations")
    return {"source": source, "review": review, "metrics": metrics}


def evaluate(folders, output):
    rows = [load_finalized(folder) for folder in folders]
    if not rows:
        raise ValueError("At least one finalized review is required")
    return _new_directory(output, lambda folder: aggregate(rows, folder))
