"""Reproducible per-content jobs with resumable stages and per-attempt records."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

from . import __version__
from .contracts import render_markdown, validate_evidence, validate_target
from . import media
from .providers import LocalModel, OllamaModel, describe, extractive_target, local_endpoint, ollama_runtime_version
from .generation import generation_schema, synthesis_messages, validate_generation
from .storage import digest, file_hash, local_path, read_json, write_json, write_text


@dataclass(frozen=True)
class Config:
    asr_model: str | None = None
    endpoint: str | None = None
    vision_model: str | None = None
    vision_revision: str | None = None
    text_model: str | None = None
    text_revision: str | None = None
    model_backend: str = "openai"
    context_tokens: int = 8192
    output_tokens: int = 2048
    model_timeout_seconds: int = 300
    ollama_threads: int | None = None
    input_kind: str = "local_video"
    frame_interval: float = 2.0
    frame_cap: int = 60

    def validate(self):
        if self.input_kind not in {"local_video", "synthetic_fixture"}:
            raise ValueError("unknown_input_kind")
        if self.model_backend not in {"openai", "ollama"}:
            raise ValueError("unknown_model_backend")
        if self.ollama_threads is not None and (self.model_backend != "ollama" or type(self.ollama_threads) is not int or not 1 <= self.ollama_threads <= 64):
            raise ValueError("ollama_threads_invalid")
        if not 2048 <= self.context_tokens <= 32768 or not 128 <= self.output_tokens <= 4096 or not 1 <= self.model_timeout_seconds <= 1200:
            raise ValueError("model_resource_limits_invalid")
        if not math.isfinite(self.frame_interval) or self.frame_interval < 0.5 or not 1 <= self.frame_cap <= 60:
            raise ValueError("invalid_frame_policy")
        if self.endpoint:
            local_endpoint(self.endpoint)
        for name in ("vision", "text"):
            if getattr(self, name + "_model") and not (self.endpoint and getattr(self, name + "_revision")):
                raise ValueError("local_endpoint_and_model_revision_required")
            if getattr(self, name + "_model") and self.model_backend == "ollama":
                OllamaModel(self.endpoint, getattr(self, name + "_model"), getattr(self, name + "_revision"), Path("."), context_tokens=self.context_tokens, output_tokens=self.output_tokens, timeout_seconds=self.model_timeout_seconds, threads=self.ollama_threads)


def versions(config):
    root = Path(__file__).parent
    source = {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*")) if p.suffix in {".py", ".json", ".txt"}}
    packages = {}
    for package in ("jsonschema", "Pillow", "faster-whisper", "av", "ctranslate2", "onnxruntime"):
        try:
            packages[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages[package] = None
    weights = {}
    if config.asr_model:
        folder = Path(config.asr_model)
        if folder.is_dir():
            weights = {p.name: file_hash(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name in {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "vocabulary.json"}}
    runtime = None
    if config.model_backend == "ollama" and config.endpoint:
        try:
            runtime = ollama_runtime_version(config.endpoint)
        except (OSError, ValueError, KeyError):
            runtime = "unavailable"
    return {"pipeline": __version__, "source_sha256": digest(source), "python": platform.python_version(), "packages": packages, "ollama": runtime, "ffmpeg": media.tool_version("ffmpeg"), "ffprobe": media.tool_version("ffprobe"), "tesseract": media.tool_version("tesseract"), "asr_files": weights}


class ProgressWriteError(OSError):
    """A failed progress commit must not become a missing evidence channel."""


class Job:
    def __init__(self, root, identity, version_info, on_progress=None):
        self.directory = local_path(root) / identity
        self.directory.mkdir(parents=True, exist_ok=True)
        self.attempt = self.directory / "attempts" / uuid.uuid4().hex
        self.attempt.mkdir(parents=True)
        self.record = {"job_id": identity, "attempt_id": self.attempt.name, "started_utc": datetime.now(timezone.utc).isoformat(), "versions": version_info, "stages": [], "transitions": [], "validation": "not_run", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "paid_cash_usd": 0, "retry_count": 0, "schema_repairs": 0}
        self.on_progress = on_progress

    def publish(self):
        try:
            write_json(self.attempt / "run.json", self.record)
            if self.on_progress:
                self.on_progress(self.attempt, json.loads(json.dumps(self.record)))
        except OSError as exc:
            raise ProgressWriteError("progress_commit_failed") from exc

    def state(self, state, reason):
        self.record["state"] = state
        self.record["transitions"].append({"state": state, "reason": reason, "utc": datetime.now(timezone.utc).isoformat()})
        self.publish()

    def stage(self, name, action):
        path = self.directory / "cache" / (name + ".json")
        started = time.monotonic()
        row = {"name": name, "cache_hit": False, "status": "failed"}
        self.record["current_stage"] = name
        self.publish()
        try:
            if path.exists():
                stored = read_json(path)
                if digest(stored["value"]) != stored["sha256"]:
                    raise ValueError("cache_integrity_failure")
                value = stored["value"]
                row["cache_hit"] = True
            else:
                value = action()
                write_json(path, {"value": value, "sha256": digest(value)})
            row["status"] = "success"
            return value
        except Exception as exc:
            row["error_category"] = type(exc).__name__
            raise
        finally:
            row["latency_seconds"] = round(time.monotonic() - started, 6)
            self.record["stages"].append(row)
            self.record["current_stage"] = None
            self.publish()


def _asr(path, model_path):
    # Isolate model loading/inference in a bounded subprocess, including iterator consumption.
    raw = media.command([sys.executable, "-m", "reel_to_md.asr", str(Path(path).resolve()), str(Path(model_path).resolve())], timeout=300)
    return json.loads(raw)


def run_video(path, output_root, config=Config(), on_progress=None):
    config.validate()
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("media_size_limit")
    version_info = versions(config)
    input_hash = file_hash(path)
    identity = digest({"source": input_hash, "config": asdict(config), "versions": version_info})
    job = Job(output_root, identity, version_info, on_progress)
    job.record["input_sha256"] = input_hash
    job.record["input_kind"] = config.input_kind
    job.record["result_kind"] = "synthetic_video_wiring" if config.input_kind == "synthetic_fixture" else "local_video_unreviewed"
    lock = job.directory / "active.lock"
    try:
        fd = lock.open("x")
    except FileExistsError:
        raise ValueError("job_active_or_interrupted_review_lock") from None
    started = time.monotonic()
    try:
        job.state("queued", "local_file_accepted")
        job.state("extracting", "bounded_local_extraction")
        info = job.stage("probe", lambda: media.probe(path))
        selected = job.stage("frames", lambda: media.frames(path, job.directory / "frames", info["duration"], config.frame_interval, config.frame_cap))
        for frame in selected["frames"]:
            frame_path = job.directory / "frames" / frame["file"]
            if not frame_path.is_file() or file_hash(frame_path) != frame["sha256"]:
                raise ValueError("cached_frame_missing_or_corrupt")
        packet = {"schema_version": "1.0", "clip_id": identity, "duration_seconds": info["duration"], "pipeline_version": __version__ + ":" + version_info["source_sha256"], "channels": {"audio": "empty" if not info["has_audio"] else "failed", "ocr": "failed", "vision": "failed"}, "truncated": selected["truncated"], "evidence": []}
        channel_errors = {}

        def model_for(name):
            args = (config.endpoint, getattr(config, name + "_model"), getattr(config, name + "_revision"), job.directory / "model-cache")
            options = {"on_usage": lambda usage: _usage(job, usage)}
            if config.model_backend == "ollama":
                return OllamaModel(*args, **options, context_tokens=config.context_tokens, output_tokens=config.output_tokens, timeout_seconds=config.model_timeout_seconds, threads=config.ollama_threads)
            return LocalModel(*args, **options)

        def channel(name, kind, action):
            try:
                entries = job.stage(name, action)
                # Validate each channel before any model consumes its output.
                candidate = {**packet, "channels": {**packet["channels"], name: "available" if entries else "empty"}, "evidence": packet["evidence"] + [{**e, "id": f"{name}-{i:04}", "kind": kind} for i, e in enumerate(entries, 1)]}
                validate_evidence(candidate)
                packet.update(candidate)
            except ProgressWriteError:
                raise
            except Exception as exc:
                channel_errors[name] = type(exc).__name__

        if info["has_audio"]:
            channel("audio", "transcript", lambda: _asr(path, config.asr_model) if config.asr_model else (_ for _ in ()).throw(ValueError("local_asr_model_not_configured")))
        channel("ocr", "ocr", lambda: media.ocr(selected["frames"], job.directory / "frames"))

        def vision():
            if not config.vision_model:
                raise ValueError("local_vision_not_configured")
            model = model_for("vision")
            entries = []
            # Deterministic first/middle/last policy frozen before model responses.
            frames = selected["frames"]
            for index in sorted({0, len(frames) // 2, len(frames) - 1}) if frames else []:
                frame = frames[index]
                text, usage = describe(model, job.directory / "frames" / frame["file"], "vision-" + str(index))
                entries.append({"start_seconds": frame["seconds"], "end_seconds": frame["seconds"], "text": text, "review_flag": "uncertain"})
            return entries

        channel("vision", "visual_description", vision)
        job.record["channel_failures"] = channel_errors
        job.record["draft_mode"] = "bound_excerpts_v1" if config.text_model else "conservative_extracts"
        validate_evidence(packet)
        write_json(job.attempt / "evidence.json", packet)
        write_json(job.attempt / "frames.json", selected)
        job.state("synthesizing", "local_model" if config.text_model else "conservative_extractive_draft")

        def synthesize():
            if not config.text_model:
                return extractive_target(packet)
            model = model_for("text")
            schema = generation_schema(packet)
            key = "text-" + digest(packet)
            text, usage = model.complete(synthesis_messages(packet), key, structured=schema)
            # Keep the original redacted response even if JSON parsing fails.
            write_text(job.attempt / "first-pass-response.txt", text)
            return json.loads(text)

        target = job.stage("target-" + digest(packet), synthesize)
        write_json(job.attempt / "first-pass-target.json", target)
        job.state("validating", "schema_semantics_and_render")
        validate_target(packet, target)
        if config.text_model:
            validate_generation(packet, target)
        write_text(job.attempt / "notes.md", render_markdown(packet, target))
        job.record["validation"] = "passed"
        job.record["result_kind"] = "synthetic_video_wiring" if config.input_kind == "synthetic_fixture" else "local_video_unreviewed"
        job.state("complete" if target["status"] == "complete" else "partial", target["status"])
    except Exception as exc:
        job.record["error_category"] = type(exc).__name__
        if job.record.get("state") == "validating":
            job.record["validation"] = "failed"
        job.state("failed", "stage_failure_see_categories")
    finally:
        job.record["latency_seconds"] = round(time.monotonic() - started, 6)
        try:
            job.publish()
        finally:
            fd.close()
            lock.unlink(missing_ok=True)
    return job.attempt, job.record


def _usage(job, usage):
    job.record.setdefault("model_calls", []).append(usage)
    if not usage["cache_hit"]:
        for key in ("input_tokens", "output_tokens"):
            previous = job.record[key]
            job.record[key] = previous + usage[key] if previous is not None and usage[key] is not None else None
