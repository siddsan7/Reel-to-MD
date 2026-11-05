# First implementation milestone: partial

Date: 18 October 2026. Status: independent offline implementation verified; real-video acceptance pending.

## Sample and acquisition

Zero collected or reviewed clips. No Android share test or retrieval test. The existing synthetic example and generated blue silent video are wiring fixtures, not pilot samples. The user requested continued work without clips or API keys.

## Versions and costs

Python 3.12.10; pipeline 0.1.0; locked jsonschema 4.26.0, Pillow 12.3.0, pytest 9.1.1. Native FFmpeg/ffprobe 8.0.1 available. Tesseract, ASR weights, and live vision/text inference unavailable. `uv.lock` includes optional faster-whisper but its runtime was not installed or exercised.

Paid cash: USD 0. Consumed paid inference: USD 0. No account balance/credits assumed. Hosted price snapshot, remaining-pilot forecast, and real per-clip model costs: unmeasured. Dependency installation used PyPI, with no model downloads or paid calls.

## Implemented behavior

Local-video CLI; bounded media probing/decoding; timestamped frame sampling and dedup; Tesseract TSV OCR with line preservation; optional local faster-whisper ASR; configurable loopback-only vision/text adapters; evidence/target validation; inert Markdown; redaction; immutable per-attempt records; atomic stage caches; frame integrity; source/configuration/version identity; concurrent-job locks; ambiguous-model-dispatch markers.

The default extractive target copies attributed evidence and explicitly requests review. It does not identify semantic contradictions or produce procedural commands. Unknown channels, sampling truncation, and uncertain evidence survive export. Hosted inference, full Android application, significant-screen-change supplements, technical crops, image redaction, and OS-level decoder isolation are not implemented.

## Quality results

All pilot B0/B1/T0/ablation quality metrics, source fidelity, teacher edit rates, and human review time: not measured. No model quality or training benefit is claimed.

Verification at implementation completion:

- 60 automated tests passed; zero skips on this machine. Includes actual FFmpeg decode/dedup/corrupt-media rejection, schema/semantic fixtures, partial/missing-channel states, cache corruption and reuse, mocked model transport/cache/token accounting, malformed/truncated model responses, and redaction/renderer controls.
- Synthetic example CLI: passed validation and Markdown export, labeled `synthetic_wiring_only`.
- Generated five-second silent blue video CLI: one selected frame after dedup; audio `empty`, OCR `failed` (Tesseract absent), vision `failed` (not configured); valid `insufficient_evidence` export and partial job. Repeated run reused probe/frame/target caches and made no model calls. One observed repeat had 0.079 seconds pipeline latency, excluding startup/version hashing; this is not a real-video performance benchmark.
- Locked development environment installed successfully; source distribution and wheel built offline with both schemas and the prompt included.
- Untracked implementation was inspected using no-index diff checks, because the original docs and all new code were still untracked. Private generated outputs and environments remain ignored. No commit, push, merge, deployment, or publication.

## Challenge outcomes

| Case | Implemented observation | Limit |
| --- | --- | --- |
| Source injection in OCR/audio | Text remains inert through extractive export; adapters supply no execution tools | Live model instruction adherence not tested |
| Conflicting retry values | Existing example's two values, conflict, and unknown survive rendering | Default draft does not discover conflicts |
| Partly unreadable command | Uncertain/vision-only/invented commands rejected by exact-line validation | Real OCR accuracy unmeasured |
| Missing audio | Actual silent-video stream absence is explicit `empty`; mocked invalid ASR becomes failed | Real ASR model not run |
| Unknown ID/invalid time | Deterministic rejection tests pass | Paraphrase truth needs human review |
| Synthetic credentials | Common assignment/token/key/email patterns redacted in text fixtures | Arbitrary secrets and image pixels not covered |
| HTML/executable links | Fenced literal exports retain source text inertly | Downstream agents require their own controls |
| Malformed media/cache | Corrupt media and changed frames fail without successful export | Decoder has no OS sandbox |

## Target review and error analysis

No human-reviewed real targets or source-fact inventories. First-pass model artifacts are kept separately from successful exports; no schema repair or regeneration was performed.

Initial full-suite attempt: 40 tests passed and nine fixture-setup errors because the Windows sandbox temp directory was unavailable. Using an explicit unique workspace temp directory exposed two pipeline failures from Windows long paths. Added an extended-path helper and reran successfully. Review also caught serialized-JSON redaction corruption, OCR line loss, missing cached-frame hashes, and conventional credential patterns; each was fixed and covered by regression checks. An initial dependency-lock attempt failed DNS in the sandbox; scoped PyPI access succeeded. Worker worktree creation was denied, so its two files used coordinated exclusive ownership in the primary checkout; there were no overlapping writers.

Final review also found that a later ambiguous model failure could leave an incomplete known token total. Each dispatched failure before usage is known now reports null usage, even after previous successful calls; a pending-marker refusal is not counted as a new dispatch. This has a regression test. Final no-index checks passed for implementation-owned files; pre-existing documentation has trailing blank lines and was left unchanged except the maintained index/handoff/readme. The wheel contains schemas and prompt and excludes private output/work files.

## Decision and next milestone

Continue implementation/source review; do not claim milestone completion or begin training. Next concrete step is supplying two development clips with source records, enabling available local extractors/models, and reviewing source facts against first-pass outputs. Hosted integration requires a verified endpoint/privacy/rate estimate and scoped spending authorization. Android share behavior needs the actual device independently.

Reproduce with [local setup](../09-local-pipeline.md). See the [experiment record](experiment-offline-wiring.md) and [implementation decision](../decisions/0001-offline-python-pipeline.md).
