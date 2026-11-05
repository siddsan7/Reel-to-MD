"""Human-label development metrics. Never infer semantic truth from a model."""
import csv
import io
from collections import defaultdict

from .contracts import _literal
from .storage import write_json, write_text


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def score(source, review):
    """Called only after review validation; labels refer to this original target."""
    units = {u["id"]: u for u in review["units"]}
    factual = [u for u in units.values() if u["factual"]]
    facts = [f for f in review["facts"] if f["source_supported"]]
    important = [f for f in facts if f["important"]]
    available = [f for f in important if f["input_available"]]

    def recovered(fact, require_input=False):
        return any(units[key]["factual"] and units[key]["source_consistent"] and (not require_input or units[key]["input_support"] == "full") for key in fact["recovered_by"])

    links = [link for u in factual for link in u["citations"]]
    evidence_ids = {e["id"] for e in source["evidence"]["evidence"]}
    technical = [f for f in facts if f["important"] and f["input_available"] and f["technical_value"] is not None]
    answerable = [f for f in facts if f["input_available"]]
    # Reference validity counts asserted references once per original output item,
    # not once per reviewer-created atomic decomposition.
    refs = []
    target = source["target"] if isinstance(source["target"], dict) else {}
    for group in ("claims", "steps", "conflicts", "unknowns", "omissions"):
        items = target.get(group, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("evidence_ids"), list):
                    refs.extend(item["evidence_ids"])
    return {
        "synthesis_recall": ratio(sum(recovered(f, True) for f in available), len(available)),
        "end_to_end_recall": ratio(sum(recovered(f) for f in important), len(important)),
        "unsupported_claim_rate": ratio(sum(u["input_support"] != "full" for u in factual), len(factual)),
        "source_error_rate": ratio(sum(not u["source_consistent"] for u in factual), len(factual)),
        "citation_support_precision": ratio(sum(link["supports"] for link in links), len(links)),
        "reference_validity": ratio(sum(isinstance(ref, str) and ref in evidence_ids for ref in refs), len(refs)),
        "technical_item_accuracy": ratio(sum(any(units[key]["factual"] and units[key]["source_consistent"] and units[key]["text"] == f["technical_value"] for key in f["recovered_by"]) for f in technical), len(technical)),
        "conflict_recall": ratio(sum(i["represented"] for i in review["conflicts"]), len(review["conflicts"])),
        "uncertainty_recall": ratio(sum(i["represented"] for i in review["gaps"]), len(review["gaps"])),
        "unnecessary_uncertainty": ratio(sum(f["incorrectly_unknown"] for f in answerable), len(answerable)),
    }


def aggregate(rows, output):
    """Cohort-separated descriptive summaries; no statistical superiority claim."""
    seen, groups, group_labels = set(), defaultdict(list), {}
    source_labels, attempts, review_ids = {}, set(), set()
    for row in rows:
        review, source = row["review"], row["source"]
        key = (review["clip_key"], review["condition"], source["variant"])
        if key in seen:
            raise ValueError("Duplicate clip/condition/variant; select one review revision")
        seen.add(key)
        if review["review_id"] in review_ids:
            raise ValueError("Duplicate review identity")
        review_ids.add(review["review_id"])
        attempt_key = (source["attempt"], source["variant"])
        if attempt_key in attempts:
            raise ValueError("Duplicate original attempt/variant under different labels")
        attempts.add(attempt_key)
        identity = (source["synthetic"], review["split"], review["source_group"])
        if review["clip_key"] in group_labels and group_labels[review["clip_key"]] != identity:
            raise ValueError("Inconsistent clip source group or cohort")
        group_labels[review["clip_key"]] = identity
        video_hash = source["run"].get("input_sha256") or (source["video"] or {}).get("sha256")
        if video_hash:
            source_label = (review["clip_key"], *identity)
            if video_hash in source_labels and source_labels[video_hash] != source_label:
                raise ValueError("Same source video has inconsistent clip identity/cohort labels")
            source_labels[video_hash] = source_label
        cohort = (source["synthetic"], review["split"], review["condition"], source["variant"])
        groups[cohort].append(row)
    cohorts = []
    for (synthetic, split, condition, variant), selected in sorted(groups.items()):
        metrics = {}
        for name in selected[0]["metrics"]:
            values = [row["metrics"][name] for row in selected]
            eligible = [m["value"] for m in values if m["value"] is not None]
            metrics[name] = {"micro": ratio(sum(m["numerator"] for m in values), sum(m["denominator"] for m in values)),
                             "macro": sum(eligible) / len(eligible) if eligible else None,
                             "eligible_clips": len(eligible)}
        cohorts.append({"synthetic": synthetic, "split": split, "condition": condition, "variant": variant,
                        "clips": len(selected), "source_groups": len({r["review"]["source_group"] for r in selected}),
                        "decisions": {d: sum(r["review"]["decision"] == d for r in selected) for d in ("accept", "edit", "reject")},
                        "observed_target_schema_valid": sum(r["source"]["validity"]["schema"] for r in selected),
                        "observed_target_semantic_valid": sum(r["source"]["validity"]["semantic"] for r in selected),
                        "metrics": metrics})
    write_json(output / "summary.json", {"scope": "human-labeled development; descriptive only", "included_reviews": len(rows),
               "not_measured": ["Unsubmitted or incomplete reviews", "Request-level first-pass validity and export success", "Audit/test generalization or confidence intervals"], "cohorts": cohorts})
    columns = ["review_id", "clip_key", "source_group", "condition", "split", "synthetic", "variant", "decision", "review_minutes"]
    names = list(rows[0]["metrics"]) if rows else []
    columns += [name + "_" + suffix for name in names for suffix in ("numerator", "denominator", "value")]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        r, s = row["review"], row["source"]
        data = {k: r[k] for k in columns[:9] if k in r}
        data.update(synthetic=s["synthetic"], variant=s["variant"])
        for name, metric in row["metrics"].items():
            data.update({name + "_" + k: ("N/A" if v is None else v) for k, v in metric.items()})
        # Prevent spreadsheet formula execution by user/source labels.
        data = {k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v) for k, v in data.items()}
        writer.writerow(data)
    write_text(output / "clip-scores.csv", stream.getvalue())
    lines = ["# Development evaluation", "", "Human labels; synthetic cohorts remain separate. N/A means a zero denominator.", ""]
    for index, cohort in enumerate(cohorts, 1):
        lines += [f"## Cohort {index}", "", _literal(f"Condition: {cohort['condition']}; partition: {cohort['split']}; variant: {cohort['variant']}"), "",
                  f"Clips: {cohort['clips']}; source groups: {cohort['source_groups']}; synthetic: {cohort['synthetic']}.", "",
                  "| Metric | Micro count | Micro value | Macro value | Eligible clips |", "| --- | --- | --- | --- | --- |"]
        for name, metric in cohort["metrics"].items():
            micro = metric["micro"]
            fmt = lambda x: "N/A" if x is None else f"{x:.3f}"
            lines.append(f"| {name} | {micro['numerator']}/{micro['denominator']} | {fmt(micro['value'])} | {fmt(metric['macro'])} | {metric['eligible_clips']} |")
        lines.append("")
    lines += ["Unsubmitted/incomplete reviews are not counted. Request-level validity/export success, frozen audits, confidence intervals, and real-video quality are not established by this report."]
    write_text(output / "report.md", "\n".join(lines))
