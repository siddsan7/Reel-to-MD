# Local model setup and checks

Date: 19 October 2026. Scope: local model installation and integration; no paid APIs, GPU rentals, training, publication, or real clips.

## Installed configuration

Whisper small.en is installed as a pinned CTranslate2 snapshot under ignored `models/whisper-small.en`. Native Ollama has Qwen3-VL-4B-Instruct Q4_K_M and Qwen3-4B-Instruct-2507 Q4_K_M. Full revisions are recorded in [local setup](../10-local-models.md) and the generated private configuration. The two Qwen models occupy about 3.30 GB and 2.50 GB on disk. ASR runs on CPU int8. Ollama runs on CPU in the measured checks and unloads models after each call.

Runtime: Python 3.12.10, Ollama 0.40.3, faster-whisper 1.2.1, PyAV 18.1.0, CTranslate2 4.8.3, ONNX Runtime 1.31.0, FFmpeg/ffprobe 8.0.1. `uv.lock` records Python dependencies. `run.json` records runtime versions, model hashes/digests, stage state/latency, validation, and usage.

## Checks and failed attempts

- 85 unit/integration tests passed, with no skips in the installed ASR environment. Includes actual WAV decoding through faster-whisper, FFmpeg media fixtures, Ollama pin checks, response handling, image conversion, generation constraints, uncertainty, cache behavior, and renderer controls.
- The actual native Ollama server rejected a synthetic 15009-token input against a 2048-token context with HTTP 400 in 3.157 seconds. Input truncation and context shifting are disabled. The retained negative check is `outputs/context-overflow-check.json`.
- Direct Whisper transcription of generated speech succeeded with valid timestamps. It preserved the value 3 and unknown execution status but misheard “retries” as “retrieves.” This is an extraction error, not corrected evidence.
- Qwen3-VL read the generated terminal text, including `max_retries = 3`, `python agent.py`, and unknown execution status. Vision extraction took about 48–53 seconds in early full runs on this CPU.
- Initial transcription failed because PyAV 19 removed `metadata_errors`, which faster-whisper uses. Reproduced the traceback, constrained `av<19`, installed 18.1.0, added a real decoder regression, and confirmed live ASR.
- First synthesis attempt: valid JSON, rejected for wrong attribution, unsupported vision-only commands, and lost uncertainty. About 131.734 seconds for the whole attempted job; ASR and OCR failed then.
- Second attempt after dependency/prompt fixes: ASR succeeded; synthesis still invented an `ocr` reference, used wrong attribution, and supplied a vision-only command. Rejected. Whole job: 166.437 seconds.
- Third attempt with packet-constrained schema: IDs/attribution improved, but an uncertain vision reference was not acknowledged; the model also copied a whole transcript sentence into the command field. Rejected. Whole job: 156.719 seconds.

All three failed jobs and their original redacted responses/targets remain in ignored `outputs/local-smoke/`. No failed output was silently repaired or exported. The final generation policy requires packet-derived uncertainty entries and limits command candidates to normal OCR lines; spoken instructions remain prose. The original validator is unchanged. Constraints reduce structural failures; arbitrary paraphrase support and cross-modal truth still require review. The validator can still reject unsupported combinations, including combined attribution citing only one evidence kind.

## Final live outcome

The final synthetic full pipeline passed the original schema/semantic validator and exported Markdown. Audio and vision were available; OCR was failed because native Tesseract is absent. Status was correctly partial. The generated six-second fixture was not counted as a real clip.

| Stage | First-run seconds | Repeat |
| --- | ---: | --- |
| Probe | 0.063 | Cached |
| Frames | 0.328 | Cached |
| Whisper ASR | 3.437 | Cached |
| OCR | 0.016 | Explicit failure; retried |
| Qwen vision | 47.859 | Cached |
| Qwen synthesis | 104.531 | Cached |
| Whole measured pipeline | 156.250 | 0.078 seconds |

First-run model usage: 3245 input tokens and 624 output tokens. Repeat: zero new input/output tokens and no inference calls. Pipeline timings exclude CLI startup, source/model hashing, and runtime-version probes. These are one synthetic job, not a latency benchmark or a quality result.

The successful immutable job is `62e0c42ffe94c765640e424edcd29a237b7e1390458c709d04c0d031430c9386`, with first attempt `1080a0ffb4874014b9f1368a3eb055e8` and repeated attempt `64974b055fc7430fadffc98fae6cc1e9`. Its summary is `outputs/local-smoke-summary.json`. The original uncertainty, missing OCR, and attributed source text survive the Markdown export.

## Docker

Added an optional CPU `Dockerfile`, allowlisted `.dockerignore`, and container-path configuration example. The image specifies Python, FFmpeg, Tesseract English, and locked ASR dependencies. It uses a nonroot runtime and expects mounted local weights. Native Ollama remains on the host, accessed through explicitly enabled host networking to retain the loopback restriction.

Docker is not installed here. Image build, Docker execution, container mount permissions, and host networking were not tested. Native Tesseract is also absent; native OCR is explicitly failed. Docker support does not claim identical performance or GPU behavior across systems.

## Cost and remaining acceptance

Paid cash and paid inference: USD 0. No provider credits or available balances assumed. CPU time and model downloads used existing hardware/network. No real-video accuracy, pilot spending forecast, teacher choice, human review time, or training improvement is measured.

Two real development clips, source records, and human review are still needed. Install native Tesseract for native OCR, or build/test the optional image on a Docker-equipped system. Follow [setup and checks](../10-local-models.md). Keep this milestone partial until the real-video gate in `HANDOFF.md` passes.
