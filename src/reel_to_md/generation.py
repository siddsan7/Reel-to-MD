"""Select literal extractions with mechanically bound citations.

The original reviewed-target contract remains unchanged and broader.
"""
from copy import deepcopy
from importlib.resources import files
import json

from jsonschema import Draft202012Validator

DRAFT_TITLE = "Selected source excerpts (unreviewed)"
REVIEW_NOTE = {"text": "These are verbatim extraction excerpts, not verified facts or inferred instructions. Recognition, relevance, completeness and source fidelity require review.", "basis": "not_provided", "evidence_ids": []}
SELECTION_NOTE = {"reason": "Only selected extraction excerpts are shown. Long lines and other details remain in the full evidence; no procedure or conflict resolution is inferred.", "evidence_ids": []}


def synthesis_messages(packet):
    prompt = files("reel_to_md").joinpath("prompts/teacher-prompt.txt").read_text(encoding="utf-8")
    return [{"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"EVIDENCE_PACKET": packet, "REQUIRED_UNKNOWNS": required_unknowns(packet) + [REVIEW_NOTE]}, ensure_ascii=False, separators=(",", ":"))}]


def required_unknowns(packet):
    """Derive explicit uncertainty requirements from the complete packet."""
    mandatory = []
    uncertain_ids = [e["id"] for e in packet["evidence"] if e["review_flag"] == "uncertain"]
    if uncertain_ids:
        mandatory.append({"text": "These extractions are uncertain and require source review.", "basis": "evidence", "evidence_ids": uncertain_ids})
    missing = [f"{name}: {state}" for name, state in packet["channels"].items() if state != "available"]
    if missing:
        mandatory.append({"text": "Unavailable channels: " + "; ".join(missing) + ".", "basis": "missing_channel", "evidence_ids": []})
    if packet["truncated"]:
        mandatory.append({"text": "Evidence extraction reached its sampling cap.", "basis": "truncated", "evidence_ids": []})
    return mandatory


def excerpt_texts(entry):
    """Use a whole short entry or whole short lines, without normalization.

    Never cut a long line, repair recognition, merge sources or remove qualifiers.
    Unselectable text stays in the evidence; selection limits remain explicit.
    """
    text = entry["text"]
    if len(text) <= 400:
        return [text] if text.strip() else []
    return list(dict.fromkeys(line for line in text.splitlines() if line.strip() and len(line) <= 400))


def generation_schema(packet):
    schema = json.loads(files("reel_to_md").joinpath("schemas/target.schema.json").read_text(encoding="utf-8"))
    properties = schema["properties"]
    properties["title"] = {"const": DRAFT_TITLE}
    properties["status"] = {"const": "partial" if packet["evidence"] else "insufficient_evidence"}
    variants = []
    attributions = {"transcript": "narration", "ocr": "screen_extraction", "visual_description": "visual_description"}
    for entry in packet["evidence"]:
        texts = excerpt_texts(entry)
        if not texts:
            continue
        for index, text in enumerate(texts):
            variant = deepcopy(properties["claims"]["items"])
            variant["properties"].update({
                "id": {"const": "excerpt-" + entry["id"] + "-" + str(index)},
                "text": {"const": text},
                "attribution": {"const": attributions[entry["kind"]]},
                "evidence_ids": {"const": [entry["id"]]},
            })
            variants.append(variant)
    properties["claims"].update({"minItems": 1 if variants else 0, "maxItems": min(8, len(variants)), "uniqueItems": True})
    if variants:
        properties["claims"]["items"] = {"oneOf": variants}
    for name in ("steps", "conflicts"):
        properties[name] = {"const": []}
    properties["unknowns"] = {"const": required_unknowns(packet) + [REVIEW_NOTE]}
    properties["omissions"] = {"const": [SELECTION_NOTE]}
    return schema


def validate_generation(packet, target):
    """Fail closed even when a local runtime ignores structured decoding."""
    error = next(Draft202012Validator(generation_schema(packet)).iter_errors(target), None)
    if error is not None:
        # Do not echo potentially private source values in diagnostics.
        raise ValueError("automatic_excerpt_binding_failed")
