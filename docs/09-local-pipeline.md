# Local pipeline setup and verification

Implementation v0.1.0, 18 October 2026. First milestone is partial pending real clips and inference/source review.

## Acceptance scope

Accept a local video up to 100 MiB, 120 seconds, and 3840×2160 pixels. Produce selected original-resolution frames, timestamped ASR/OCR/vision evidence, schema-valid notes, inert Markdown, and a run record. Missing channels remain explicit; invalid media or invalid generated targets must never produce a successful export. Repeating the same input/configuration/version reuses completed work. Validate contracts before enabling hosted or paid inference.

The implemented default produces an extractive draft. It copies evidence with attribution, makes no procedural commands or conflict-resolution claims, and explicitly requires human review. This establishes pipeline wiring; it does not meet the two-real-clip quality gate.

## Environment

Use Python 3.12 and uv. `uv.lock` locks the core, development, and optional ASR dependency graph. The tested environment uses Python 3.12.10 on Windows. Install uv if it is unavailable; then:

```powershell
python -m uv sync --locked
.venv/Scripts/reel-to-md --help
.venv/Scripts/reel-to-md check-example docs/examples/example.json
.venv/Scripts/reel-to-md run data/private/development/code.mp4
```

FFmpeg and ffprobe must be on PATH. Tesseract must be on PATH with English language data for OCR. These native binaries are outside the Python lock; their version strings are recorded per job. FFmpeg 8.0.1 was available during implementation; Tesseract was unavailable. See official [FFmpeg options](https://ffmpeg.org/ffmpeg.html), [Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), and [uv locking/syncing](https://docs.astral.sh/uv/concepts/projects/sync/).

To enable ASR, install the locked optional group and point configuration at an existing local CTranslate2 Whisper model directory:

```powershell
python -m uv sync --locked --extra asr
```

ASR uses CPU int8, English, beam size 5, VAD, and a 300-second subprocess timeout. Model files are hashed in the job identity. The adapter uses `local_files_only=True`; the CLI does not download weights. See [faster-whisper's upstream model usage](https://github.com/SYSTRAN/faster-whisper). ASR was not run against model weights in this implementation session.

## Configuration

Pass `--config data/private/local-config.json`. All fields are optional; omitted model fields disable that adapter. A minimal ASR-only configuration is `{"asr_model": "C:/private/models/whisper-small"}`.

Example with an existing local OpenAI-compatible server:

```json
{
  "asr_model": "C:/private/models/whisper-small",
  "endpoint": "http://127.0.0.1:8080/v1",
  "vision_model": "your-local-vision-model",
  "vision_revision": "exact-local-weight-revision",
  "text_model": "your-local-text-model",
  "text_revision": "exact-local-weight-revision",
  "frame_interval": 2.0,
  "frame_cap": 60
}
```

Model names above are placeholders. Configure only models already available on your own hardware; ensure the server does not proxy to a paid or external service. The endpoint must use HTTP with literal loopback `127.0.0.1` or `::1`. Redirects, proxies, endpoint credentials, URL intake, hosted models, and automatic retries are disabled. No model tools are supplied. Responses are capped at 4096 output tokens and 2 MiB, with a 120-second HTTP timeout. Text uses the versioned teacher prompt and output schema. Vision extracts the first/middle/last selected frames, at most three, and marks descriptions uncertain. Raw images go only to the explicitly configured local server; image redaction is not implemented.

Uniform sampling defaults to every two seconds and 60 candidates. Thumbnail mean-difference deduplication keeps changed frames; OCR deduplicates consecutive identical texts while preserving line breaks. Significant-screen-change supplementation, technical crops, and human preselection of informative frames remain future work. Sampling cannot establish that every important event was seen.

## Artifacts and resuming

The default output is `outputs/jobs/<content-and-config-hash>/`. Keep this private and ignored by Git.

- `frames/`: selected PNGs; `cache/frames.json` contains timestamps, policy, frame hashes, and truncation.
- `cache/`: successful probe/channel/target stages, each with an integrity digest.
- `model-cache/`: redacted first responses, usage, completed local responses, and in-flight markers.
- `attempts/<id>/`: immutable evidence packet, frame manifest, first-pass target, validated Markdown, and `run.json` for each attempt.

Job identity includes source bytes, configuration, source/prompt/schema hashes, package versions, tool versions, and local ASR file hashes. Changing any creates a new job. Failed extraction stages can be attempted on rerun, while successful stages and individual completed model responses are reused. Corrupt stage caches or missing/changed selected frames fail visibly.

`run.json` records transitions, stage latency/cache status, versions, channel errors, validation, usage, and local cost/cash of zero. Unknown token usage is null. Cached attempts count no new tokens. No invoices, credit balance, local electricity cost, or hosted-price forecasts are implied. Failures use non-sensitive error classes; private first-pass artifacts retain review context. The synthetic checker has a separately labeled, smaller wiring-check record.

`active.lock` prevents overlapping writers. A process killed mid-job may leave it behind: check that no process is running before removing that job's lock. A model `.pending` marker means dispatch began but completion is ambiguous. Inspect the local server and retained response/usage first; remove that marker only when you have explicitly decided to retry. The pipeline performs no automatic model/schema repairs and retains the first result for review.

## Validation and safety limits

Both JSON schemas are packaged with the application. Semantic checks reject duplicate IDs, non-finite/out-of-range/reversed times, inconsistent channel availability, unknown references, wrong attribution, nonconsecutive steps, unsupported exact commands, and lost uncertainty. An exact command must be a complete line in cited normal transcript/OCR evidence. Human review remains necessary to establish that a paraphrase is supported and that extraction matches the source.

All untrusted Markdown fields use dynamically sized fenced text blocks. HTML, executable links, images, and source directives remain inert text. Common credentials and email addresses receive consistent redaction placeholders before text inference and export. This is best effort; manual privacy review is required. Models have no execution tools, and extracted commands are never executed.

Decoders run as bounded subprocesses with local-only protocol allowlists, but this is not an OS-level decoder sandbox. ASR has a bounded subprocess. Keep native decoders patched and use a dedicated restricted environment before processing hostile uploads or exposing a service. No Android, retrieval, authentication, cloud storage, retention service, deployment, or training is implemented.

## Checks

```powershell
$testTempPath = Join-Path (Get-Location) ('work/pytest-' + [guid]::NewGuid().ToString('N'))
.venv/Scripts/python -m pytest -q --basetemp=$testTempPath
.venv/Scripts/reel-to-md check-example docs/examples/example.json
```

The explicit workspace temporary directory avoids Windows sandbox temp-directory restrictions. FFmpeg integration is skipped if its binaries are absent. Generated silent media and mocked provider responses are synthetic fixtures, never collected clips or model-quality results. See [measured implementation results](reports/milestone-1.md).

## Inputs needed next

Provide two accessible development videos: one code/terminal tutorial and one diagram/workflow tutorial. For each, record source URL or file origin, creator/source group, acquisition date, and intended-use permission status (including unknown). These fields are an honest source record; public availability alone does not establish permission to redistribute. Keep populated records in `data/private`, using the intake template.

Then choose existing local ASR/vision/text models and a human source reviewer, or authorize a specific hosted endpoint, price estimate, and scope before paid work. Credentials belong in private configuration, never chat. An actual Android Instagram share test remains a separate device-dependent task. Real acceptance requires source-fact inventories, reviewed outputs, original-versus-repaired scoring, and cost forecasting for both clips.
