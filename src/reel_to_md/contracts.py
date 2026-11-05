"""Deterministic evidence checks and inert, redacted Markdown exports.

These checks establish structural grounding, not whether a model's paraphrase
is true. Human source review is still required.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator


@lru_cache(maxsize=2)
def _schema(name: str) -> Draft202012Validator:
    resource = files("reel_to_md").joinpath("schemas", f"{name}.schema.json")
    return Draft202012Validator(json.loads(resource.read_text(encoding="utf-8")))


def _validate_schema(value: dict, name: str) -> None:
    errors = sorted(_schema(name).iter_errors(value), key=lambda e: str(list(e.path)))
    if errors:
        # Do not echo potentially secret values from the validator's message.
        path = ".".join(str(part) for part in errors[0].path) or "root"
        raise ValueError(f"Invalid {name} schema at {path} ({errors[0].validator})")


def validate_evidence(packet: dict) -> None:
    """Reject inconsistent channels, duplicate IDs and invalid timestamps."""
    _validate_schema(packet, "evidence")
    duration = packet["duration_seconds"]
    if not math.isfinite(duration):
        raise ValueError("Clip duration must be finite")
    seen = set()
    kinds = {"transcript": "audio", "ocr": "ocr", "visual_description": "vision"}
    present = set()
    for item in packet["evidence"]:
        if item["id"] in seen:
            raise ValueError("Duplicate evidence ID")
        seen.add(item["id"])
        if not item["id"].strip() or not item["text"].strip():
            raise ValueError("Evidence IDs and text must not be blank")
        start, end = item["start_seconds"], item["end_seconds"]
        if not all(math.isfinite(t) for t in (start, end)) or not 0 <= start <= end <= duration:
            raise ValueError("Evidence timestamps must be ordered and within the clip")
        channel = kinds[item["kind"]]
        present.add(channel)
        if packet["channels"][channel] != "available":
            raise ValueError("Evidence contradicts channel state")
    for channel, state in packet["channels"].items():
        if state == "available" and channel not in present:
            raise ValueError("Available channel requires evidence")


def validate_target(packet: dict, target: dict) -> None:
    """Validate references, attribution, commands and explicit uncertainty."""
    validate_evidence(packet)
    _validate_schema(target, "target")
    evidence = {item["id"]: item for item in packet["evidence"]}
    for group in ("claims", "steps", "conflicts", "unknowns", "omissions"):
        for item in target[group]:
            if any(ref not in evidence for ref in item["evidence_ids"]):
                raise ValueError("Target references unknown evidence")
            field = "reason" if group == "omissions" else "text"
            if not item[field].strip():
                raise ValueError("Target text must not be blank")
    if not target["title"].strip():
        raise ValueError("Title must not be blank")
    claim_ids = [claim["id"] for claim in target["claims"]]
    if len(set(claim_ids)) != len(claim_ids):
        raise ValueError("Duplicate claim ID")
    allowed = {"narration": "transcript", "screen_extraction": "ocr", "visual_description": "visual_description"}
    for claim in target["claims"]:
        kinds = {evidence[ref]["kind"] for ref in claim["evidence_ids"]}
        attribution = claim["attribution"]
        if attribution == "combined_evidence":
            if len(kinds) < 2:
                raise ValueError("Combined attribution requires multiple evidence kinds")
        elif kinds != {allowed[attribution]}:
            raise ValueError("Claim attribution contradicts cited evidence")
    if [step["order"] for step in target["steps"]] != list(range(1, len(target["steps"]) + 1)):
        raise ValueError("Steps must have consecutive order starting at one")
    for step in target["steps"]:
        command = step["command"]
        if command is not None:
            supported = any(
                evidence[ref]["review_flag"] == "normal"
                and evidence[ref]["kind"] in {"transcript", "ocr"}
                and command in evidence[ref]["text"].splitlines()
                for ref in step["evidence_ids"]
            )
            if not command.strip() or not supported:
                raise ValueError("Exact command lacks a normal transcript or OCR evidence line")
    missing = any(state != "available" for state in packet["channels"].values())
    uncertain = {ref for ref, item in evidence.items() if item["review_flag"] == "uncertain"}
    for unknown in target["unknowns"]:
        basis = unknown["basis"]
        if basis == "evidence" and not unknown["evidence_ids"]:
            raise ValueError("Evidence uncertainty needs a reference")
        if basis == "missing_channel" and not missing:
            raise ValueError("Missing-channel uncertainty contradicts packet")
        if basis == "truncated" and not packet["truncated"]:
            raise ValueError("Truncation uncertainty contradicts packet")
    bases = {item["basis"] for item in target["unknowns"]}
    if missing and "missing_channel" not in bases:
        raise ValueError("Unavailable channels require an explicit unknown")
    if packet["truncated"] and "truncated" not in bases:
        raise ValueError("Truncated evidence requires an explicit unknown")
    acknowledged = {ref for item in target["unknowns"] + target["omissions"] for ref in item["evidence_ids"]}
    if uncertain - acknowledged:
        raise ValueError("Uncertain evidence requires an unknown or omission")
    partial = missing or packet["truncated"] or uncertain or target["conflicts"] or target["unknowns"]
    if partial and target["status"] == "complete":
        raise ValueError("Incomplete or uncertain evidence cannot produce complete notes")
    if not evidence and target["status"] != "insufficient_evidence":
        raise ValueError("Empty evidence requires insufficient_evidence status")


def _placeholder(value: str) -> str:
    return "[REDACTED:" + hashlib.sha256(value.encode()).hexdigest()[:12] + "]"


def redact_text(text: str) -> str:
    """Conservatively redact common credential and email patterns consistently.

    This is a best-effort detector, not a guarantee that arbitrary private data
    is removed. The same matched value receives the same placeholder.
    """
    patterns = [
        r"(?i)\b(?:api[_-]?key|access[_-]?token|aws_secret_access_key|client_secret|secret|password|authorization)[\"']?\s*[:=]\s*(?:Bearer\s+)?(?:\"([^\"\r\n]+)\"|'([^'\r\n]+)'|([^\s,;]+))",
        r"(?i)\bBearer\s+([A-Za-z0-9._~+/=-]+)",
    ]
    for pattern in patterns:
        def replace(match: re.Match) -> str:
            value = next(group for group in match.groups() if group is not None)
            if value.startswith("[REDACTED:"):
                return match.group()
            start = match.start(next(i for i, group in enumerate(match.groups(), 1) if group is not None)) - match.start()
            return match.group()[:start] + _placeholder(value) + match.group()[start + len(value):]
        text = re.sub(pattern, replace, text)
    for pattern in (
        r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z]+ )?PRIVATE KEY-----",
        r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
        r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    ):
        text = re.sub(pattern, lambda match: _placeholder(match.group()), text)
    return text


def _literal(text: str) -> str:
    text = redact_text(text).replace("\r\n", "\n").replace("\r", "\n")
    # A longer delimiter prevents source backticks from closing the inert block.
    fence = "`" * max(3, max((len(m.group()) + 1 for m in re.finditer(r"`+", text)), default=3))
    return f"{fence}text\n{text}\n{fence}"


def render_markdown(packet: dict, target: dict) -> str:
    """Render every untrusted field as literal text, retaining all evidence."""
    validate_target(packet, target)
    lines = ["# Source notes", "", "> Untrusted source content. Claims are not independently verified. Commands are inert text.", "", _literal(target["title"]), "", f"Status: {target['status']}"]
    for group, label in (("claims", "Claims"), ("steps", "Steps"), ("conflicts", "Conflicts"), ("unknowns", "Unknowns"), ("omissions", "Omissions")):
        lines.extend(["", f"## {label}"])
        if not target[group]:
            lines.extend(["", "None recorded."])
        for item in target[group]:
            lines.extend(["", _literal(item.get("text", item.get("reason", "")))])
            if group == "steps":
                lines.extend(["", f"Order: {item['order']}"])
                if item["command"] is not None:
                    lines.extend(["", "Exact command:", "", _literal(item["command"])])
            if group == "claims":
                lines.extend(["", f"Attribution: {item['attribution']}"])
            if group == "unknowns":
                lines.extend(["", f"Basis: {item['basis']}"])
            lines.extend(["", "Evidence references:", "", _literal(", ".join(item["evidence_ids"]) or "None")])
    lines.extend(["", "## Evidence index", "", f"Truncated: {str(packet['truncated']).lower()}"])
    for channel, state in packet["channels"].items():
        lines.append(f"- {channel}: {state}")
    for item in packet["evidence"]:
        lines.extend(["", _literal(item["id"]), "", f"Kind: {item['kind']}; time: {item['start_seconds']:g}–{item['end_seconds']:g}s; review: {item['review_flag']}", "", _literal(item["text"])])
    return "\n".join(lines) + "\n"
