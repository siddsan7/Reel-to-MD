# Decision record: offline Python milestone

Status: accepted for implementation. Date: 18 October 2026. Owner: implementation agent under the user's request to begin milestone one.

## Problem and alternatives

The repository had contracts and plans but no runnable pipeline, real clips, verified credentials, or inference hardware. Building Android or paid integrations would delay independently verifiable contract work. Alternatives were a hosted-first pipeline or a synthetic-only validator.

## Evidence and tradeoffs

Python 3.12, FFmpeg 8.0.1, and uv were available. Tesseract and ASR weights were unavailable. Chosen: a locked Python CLI with real local extraction adapters, explicit partial states, deterministic schema/semantic checks, safe rendering, local-only model adapters, and a conservative extractive fallback. Provider transport is tested with mocks; it is not a live inference result.

Uniform two-second sampling with thumbnail dedup is the initial reproducible policy. The three-frame vision subset is first/middle/last; significant-screen-change supplements and human-selected informative frames are deferred and documented. No training or spending is authorized by this decision.

## Choice and reversal condition

Keep the first milestone partial until two real clips have reviewed outputs and source-fact inventories. Add hosted providers only after endpoint/privacy/rate verification and scoped spending approval. Revisit frame policy, model choice, and OCR thresholds using development clips only. Maintain the same evidence/output contracts across providers.
