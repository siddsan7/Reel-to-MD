"""Synthetic human-label simulations; no real-video quality scores."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from reel_to_md.cli import main
from reel_to_md.evaluation import score
from reel_to_md.evaluation import aggregate
from reel_to_md.review import initialize, finalize, evaluate, load_finalized, validate_review
from reel_to_md.review_page import render_page
from reel_to_md.storage import digest, file_hash, read_json, write_json


@pytest.fixture
def draft(tmp_path):
    example = read_json(Path(__file__).parents[1] / "docs/examples/example.json")
    attempt = tmp_path / "job/attempts/original"
    write_json(attempt / "evidence.json", example["input"])
    write_json(attempt / "first-pass-target.json", example["target"])
    write_json(attempt / "run.json", {"job_id": "fixture", "result_kind": "synthetic_video_wiring", "validation": "passed"})
    folder = initialize(attempt, tmp_path / "draft")
    return folder, read_json(folder / "source.json"), read_json(folder / "review.json")


def label(source, review):
    """Deliberately simulated annotations for testing workflow mechanics only."""
    review.update(reviewer="Synthetic test reviewer", clip_key="fixture-1", source_group="synthetic-creator", condition="B1",
                  source_reviewed=True, source_matches_attempt=True, unit_coverage_confirmed=True,
                  reference_inventory_complete=True, decision="accept")
    for unit in review["units"]:
        unit.update(factual=True, input_support="full", source_consistent=True)
        for citation in unit["citations"]:
            citation["supports"] = True
    return review


def complete(draft, tmp_path, decision="accept"):
    folder, source, review = draft
    label(source, review)
    review["decision"] = decision
    write_json(folder / "review.json", review)
    result = finalize(folder / "review.json", tmp_path / "final")
    return result, source, review


def fact(id, text, recovered_by, **changes):
    result = dict(id=id, text=text, important=True, source_supported=True, input_available=True,
                  recovered_by=recovered_by, technical_value=None, incorrectly_unknown=False)
    result.update(changes)
    return result


def test_init_pending_and_separate_original(draft, tmp_path):
    folder, source, review = draft
    assert not review["source_reviewed"] and review["decision"] == "pending"
    assert source["validity"] == {"schema": True, "semantic": True}
    assert {u["path"] for u in review["units"]} >= {"/title", "/steps/1/command", "/unknowns/0/text", "/conflicts/0/text"}
    with pytest.raises(ValueError, match="identity|incomplete"):
        finalize(folder / "review.json", tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()
    with pytest.raises(ValueError, match="separate"):
        initialize(source["attempt"], Path(source["attempt"]) / "review")


def test_finalization_scores_original_and_refuses_overwrite(draft, tmp_path):
    folder, source, review = draft
    label(source, review)
    before = {name: file_hash(Path(source["attempt"]) / name) for name in source["original_hashes"]}
    review["decision"] = "edit"
    review["corrected_target"] = deepcopy(source["target"])
    review["corrected_target"]["title"] = "A separately corrected title"
    original_unit = review["units"][1]
    original_unit["input_support"] = "none"
    write_json(folder / "review.json", review)
    result = finalize(folder / "review.json", tmp_path / "final")
    row = load_finalized(result)
    assert read_json(result / "reviewed-target.json")["title"] != source["target"]["title"]
    assert row["source"]["target"] == source["target"]
    assert row["metrics"]["unsupported_claim_rate"]["numerator"] == 1
    assert before == {name: file_hash(Path(source["attempt"]) / name) for name in before}
    with pytest.raises(ValueError, match="exists"):
        finalize(folder / "review.json", result)


def test_rejects_still_count_original_outputs(draft, tmp_path):
    result, source, review = complete(draft, tmp_path, "reject")
    assert not (result / "reviewed-notes.md").exists()
    evaluate([result], tmp_path / "evaluation")
    summary = read_json(tmp_path / "evaluation/summary.json")
    assert summary["cohorts"][0]["clips"] == 1
    assert summary["cohorts"][0]["metrics"]["unsupported_claim_rate"]["micro"]["denominator"] == len(review["units"])


@pytest.mark.parametrize("mutation, message", [
    (lambda r: r.update(source_reviewed=False), "attestations"),
    (lambda r: r["units"].pop(0), "omit"),
    (lambda r: r["units"][0].update(text="fabricated text"), "literal span"),
    (lambda r: r["units"][0].update(source_consistent=None), "incomplete"),
    (lambda r: r["units"][1]["citations"].clear(), "Citation"),
    (lambda r: r["units"].append(deepcopy(r["units"][0])), "Duplicate"),
    (lambda r: r["units"][0].update(factual=False), "reason"),
    (lambda r: r.update(split="development"), "challenge"),
    (lambda r: r.update(review_minutes=float("nan")), "incomplete"),
])
def test_incomplete_or_biased_annotations_rejected(draft, mutation, message):
    _, source, review = draft
    label(source, review)
    mutation(review)
    with pytest.raises(ValueError, match=message):
        validate_review(source, review)


def test_source_snapshot_and_attempt_tampering_rejected(draft, tmp_path):
    folder, source, review = draft
    label(source, review)
    changed = deepcopy(source)
    changed["target"]["title"] = "tampered"
    with pytest.raises(ValueError, match="snapshot"):
        validate_review(changed, review)
    write_json(folder / "review.json", review)
    write_json(Path(source["attempt"]) / "run.json", {})
    with pytest.raises(ValueError, match="Original attempt"):
        finalize(folder / "review.json", tmp_path / "bad")


def test_unsupported_corrected_command_is_rejected(draft):
    _, source, review = draft
    label(source, review)
    review["decision"] = "edit"
    review["corrected_target"] = deepcopy(source["target"])
    review["corrected_target"]["steps"][1]["command"] = "python fabricated.py"
    with pytest.raises(ValueError, match="Exact command"):
        validate_review(source, review)


def test_recall_denominators_exactness_and_source_vs_input(draft):
    _, source, review = draft
    label(source, review)
    first, second = review["units"][:2]
    first.update(input_support="partial", source_consistent=True)
    second.update(input_support="full", source_consistent=False)
    review["facts"] = [fact("f1", "Fact in input", [first["id"]]),
                       fact("f2", "Lost extraction fact", [], input_available=False),
                       fact("f3", "Not source supported", [], source_supported=False)]
    review["facts"].append(fact("f4", "Exact title", [first["id"]], technical_value=first["text"].lower()))
    validate_review(source, review)
    metrics = score(source, review)
    assert metrics["synthesis_recall"] == {"numerator": 0, "denominator": 2, "value": 0}
    assert metrics["end_to_end_recall"]["numerator"] == 2
    assert metrics["end_to_end_recall"]["denominator"] == 3
    assert metrics["technical_item_accuracy"]["value"] == 0  # Case is significant.
    assert metrics["source_error_rate"]["numerator"] == 1
    assert metrics["unsupported_claim_rate"]["numerator"] == 1
    assert metrics["conflict_recall"]["value"] is None
    assert metrics["unnecessary_uncertainty"]["denominator"] == 2


def test_duplicate_fact_match_and_pending_gap_rejected(draft):
    _, source, review = draft
    label(source, review)
    review["facts"] = [fact("f1", "One fact", ["missing-unit"])]
    with pytest.raises(ValueError, match="Fact matches"):
        validate_review(source, review)
    review["facts"] = [fact("f1", "One fact", [])] * 2
    with pytest.raises(ValueError, match="Duplicate reference"):
        validate_review(source, review)
    review["facts"] = []
    review["gaps"] = [dict(id="g1", text="Unknown execution", represented=None, output_paths=[])]
    with pytest.raises(ValueError, match="judgment"):
        validate_review(source, review)


def test_zero_denominators_and_duplicate_aggregation(draft, tmp_path):
    result, _, _ = complete(draft, tmp_path)
    evaluate([result], tmp_path / "scores")
    metrics = read_json(tmp_path / "scores/summary.json")["cohorts"][0]["metrics"]
    assert metrics["synthesis_recall"]["micro"]["value"] is None
    assert metrics["synthesis_recall"]["eligible_clips"] == 0
    assert "N/A" in (tmp_path / "scores/clip-scores.csv").read_text()
    with pytest.raises(ValueError, match="Duplicate clip"):
        evaluate([result, result], tmp_path / "duplicate")
    assert not (tmp_path / "duplicate").exists()


def test_finalized_annotation_tamper_rejected(draft, tmp_path):
    result, _, _ = complete(draft, tmp_path)
    write_json(result / "scores.json", {})
    with pytest.raises(ValueError, match="integrity"):
        load_finalized(result)


def test_html_source_injection_remains_encoded(draft):
    _, source, review = draft
    source["evidence"]["evidence"][0]["text"] = '</script><img src="https://example.invalid/leak" onerror="alert(1)">'
    html = render_page(source, review)
    assert source["evidence"]["evidence"][0]["text"] not in html
    assert "connect-src 'none'" in html and "script-src 'sha256-" in html
    assert "innerHTML" not in html and "fetch(" not in html
    assert html.count("<script>") == html.count("</script>") == 1


def test_natural_clip_requires_video_and_matching_hash(draft, tmp_path):
    folder, source, review = draft
    label(source, review)
    source["synthetic"] = False
    source["run"]["result_kind"] = "local_video_unreviewed"
    review["source_digest"] = digest(source)
    review["split"] = "development"
    with pytest.raises(ValueError, match="hashed original"):
        validate_review(source, review)
    video = tmp_path / "original.mp4"
    video.write_bytes(b"fixture-only-not-media")
    run = read_json(Path(source["attempt"]) / "run.json")
    run.update(input_kind="local_video", result_kind="local_video_unreviewed", input_sha256="0" * 64)
    write_json(Path(source["attempt"]) / "run.json", run)
    with pytest.raises(ValueError, match="Video hash"):
        initialize(source["attempt"], tmp_path / "mismatch", video=video)


def test_cli_review_workflow(draft, tmp_path):
    folder, source, review = draft
    label(source, review)
    write_json(folder / "annotations.json", review)
    assert main(["review-finalize", str(folder / "annotations.json"), "--output", str(tmp_path / "cli-final")]) == 0
    assert main(["evaluate", str(tmp_path / "cli-final"), "--output", str(tmp_path / "cli-scores")]) == 0
    assert main(["evaluate", str(tmp_path / "cli-final"), "--output", str(tmp_path / "cli-scores")]) == 1


def test_review_page_interactions_without_browser(draft, tmp_path):
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Optional Node.js page smoke test")
    _, source, review = draft
    # DOM selection offsets use UTF-16; persisted spans use Unicode code points.
    review["units"][0].update(text="🙂 A B", end=5)
    page = render_page(source, review)
    script = page.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    path = tmp_path / "page.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run([executable, str(Path(__file__).with_name("review_page_smoke.cjs")), str(path)], capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_missing_first_pass_is_not_dropped_or_counted_as_perfect(draft, tmp_path):
    _, source, _ = draft
    attempt = Path(source["attempt"])
    (attempt / "first-pass-target.json").unlink()
    write_json(attempt / "run.json", {"job_id": "failed-fixture", "result_kind": "synthetic_video_wiring", "state": "failed"})
    folder = initialize(attempt, tmp_path / "failed-review")
    source, review = read_json(folder / "source.json"), read_json(folder / "review.json")
    label(source, review)
    review["decision"] = "reject"
    review["facts"] = [fact("f1", "Omitted source fact", [])]
    write_json(folder / "review.json", review)
    final = finalize(folder / "review.json", tmp_path / "failed-final")
    row = load_finalized(final)
    assert not source["validity"]["schema"] and not source["validity"]["semantic"]
    assert row["metrics"]["synthesis_recall"]["value"] == 0
    assert row["metrics"]["unsupported_claim_rate"]["value"] is None


def test_natural_video_and_frame_assets_are_copied_and_verified(draft, tmp_path):
    _, source, _ = draft
    attempt = Path(source["attempt"])
    video = tmp_path / "source.mp4"
    video.write_bytes(b"synthetic-unit-fixture-for-video-identity")
    run = read_json(attempt / "run.json")
    run.update(input_kind="local_video", result_kind="local_video_unreviewed", input_sha256=file_hash(video))
    write_json(attempt / "run.json", run)
    original_frame = attempt.parent.parent / "frames/frame.png"
    original_frame.parent.mkdir()
    original_frame.write_bytes(b"frame-fixture")
    write_json(attempt / "frames.json", {"frames": [{"file": "frame.png", "seconds": 2, "sha256": file_hash(original_frame)}]})
    folder = initialize(attempt, tmp_path / "video-review", video=video)
    source, review = read_json(folder / "source.json"), read_json(folder / "review.json")
    label(source, review)
    review["split"] = "development"
    assert source["video_matches_run"] is True
    assert len(source["assets"]) == 2
    write_json(folder / "review.json", review)
    final = finalize(folder / "review.json", tmp_path / "with-assets")
    assert load_finalized(final)["source"]["video_matches_run"] is True
    (final / source["assets"][0]["file"]).write_bytes(b"changed-final-video")
    with pytest.raises(ValueError, match="integrity"):
        load_finalized(final)
    (folder / source["assets"][0]["file"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="asset integrity"):
        finalize(folder / "review.json", tmp_path / "wrong-video")


def test_macro_micro_cohorts_and_csv_safety(draft, tmp_path):
    _, source, review = draft
    label(source, review)
    review["condition"] = "=HYPERLINK(unsafe)"
    a = {"source": source, "review": review, "metrics": {"recall": {"numerator": 1, "denominator": 1, "value": 1}}}
    b = deepcopy(a)
    b["source"]["attempt"] = "other-attempt"
    b["review"]["clip_key"] = "other-clip"
    b["review"]["review_id"] = "review-b"
    b["metrics"]["recall"] = {"numerator": 1, "denominator": 3, "value": 1 / 3}
    c = deepcopy(b)
    c["source"]["attempt"] = "natural-attempt"
    c["source"]["synthetic"] = False
    c["review"].update(clip_key="natural-clip", split="development", review_id="review-c")
    aggregate([a, b, c], tmp_path)
    cohorts = read_json(tmp_path / "summary.json")["cohorts"]
    assert len(cohorts) == 2
    metrics = next(c for c in cohorts if c["synthetic"])["metrics"]["recall"]
    assert metrics["micro"]["value"] == 0.5
    assert metrics["macro"] == pytest.approx(2 / 3)
    assert "'=HYPERLINK" in (tmp_path / "clip-scores.csv").read_text()
    assert "```text" in (tmp_path / "report.md").read_text()


def test_same_source_cannot_be_recounted_by_relabeling(draft, tmp_path):
    _, source, review = draft
    label(source, review)
    source["run"]["input_sha256"] = "known-video"
    a = {"source": source, "review": review, "metrics": score(source, review)}
    b = deepcopy(a)
    b["review"].update(clip_key="fake-second-clip", condition="B0", review_id="different-review")
    with pytest.raises(ValueError, match="Duplicate original"):
        aggregate([a, b], tmp_path)
    b["source"]["attempt"] = "another-attempt"
    with pytest.raises(ValueError, match="inconsistent clip"):
        aggregate([a, b], tmp_path)


def test_atomic_coverage_preserves_operators_and_repeated_occurrences(draft):
    _, source, review = draft
    label(source, review)
    source["candidates"][0]["text"] = "--force"
    source["target"]["title"] = "--force"
    review["units"][0].update(text="force", start=2, end=7)
    review["source_digest"] = digest(source)
    with pytest.raises(ValueError, match="omit"):
        validate_review(source, review)
    source["candidates"][0]["text"] = "go go"
    source["target"]["title"] = "go go"
    review["units"][0].update(text="go", start=0, end=2)
    repeated = deepcopy(review["units"][0])
    repeated.update(id="repeat", start=3, end=5)
    review["source_digest"] = digest(source)
    with pytest.raises(ValueError, match="omit"):
        validate_review(source, review)
    review["units"].append(repeated)
    validate_review(source, review)


def test_reference_validity_counts_bad_links_even_in_invalid_empty_output(draft):
    _, source, review = draft
    label(source, review)
    original = score(source, review)["reference_validity"]
    source["target"]["claims"].append({"text": "", "evidence_ids": ["missing", {"invalid": "shape"}]})
    changed = score(source, review)["reference_validity"]
    assert changed["numerator"] == original["numerator"]
    assert changed["denominator"] == original["denominator"] + 2


def test_malformed_reference_occurrences_remain_reviewable_and_counted(draft, tmp_path):
    _, source, review = draft
    label(source, review)
    baseline = score(source, review)["citation_support_precision"]
    attempt = Path(source["attempt"])
    target = read_json(attempt / "first-pass-target.json")
    target["claims"][0]["evidence_ids"] = ["a1", 5, "", {"invalid": "shape"}]
    write_json(attempt / "first-pass-target.json", target)
    folder = initialize(attempt, tmp_path / "malformed-review")
    source, review = read_json(folder / "source.json"), read_json(folder / "review.json")
    label(source, review)
    review["decision"] = "reject"
    assert not source["validity"]["schema"]
    unit = next(u for u in review["units"] if u["path"] == "/claims/0/text")
    with pytest.raises(ValueError, match="nonexistent"):
        validate_review(source, review)
    for citation in unit["citations"][1:]:
        citation["supports"] = False
    write_json(folder / "review.json", review)
    result = finalize(folder / "review.json", tmp_path / "malformed-final")
    metrics = load_finalized(result)["metrics"]
    assert metrics["citation_support_precision"]["denominator"] == baseline["denominator"] + 3
    assert metrics["citation_support_precision"]["numerator"] == baseline["numerator"]
