# Container OCR and CPU inference fixes

Date: 19 October 2026. Goal: run the same local synthetic ASR/OCR/vision/synthesis workflow inside Docker. Native execution remains supported. No paid APIs, GPU rental, model changes, host networking, publication, or real-video quality claims.

Acceptance: required channels available; unchanged schema and semantic validation pass; exact command recovered by OCR without text correction; valid Markdown exported; replay uses cached stages with zero new model tokens. Keep the 300-second call timeout, context/output limits, original models, and original failed artifacts. Stop if the bounded test fails; reassess using new evidence rather than retrying the same request.

## Diagnosis and changes

The earlier server used 16 inference threads inside an eight-CPU quota. Its logs showed inference progress and no OOM kill. CPU quota controls available CPU time but did not constrain the thread count chosen by this runtime. An affinity-only diagnostic (`run-6c4598eb43`) still logged 16 inference threads, so it was stopped early instead of waiting for another timeout. Its logs and original artifacts remain available; no successful model result is claimed for it.

The next test adds explicit `ollama_threads` configuration, passed as the model API's `num_thread` option. This option is defined in [Ollama 0.40.3's API source](https://github.com/ollama/ollama/blob/v0.40.3/api/types.go). Values must be integers from 1 to 64; they apply only to the Ollama backend. The default remains automatic for native users. Configuration participates in job identity, so changing the thread count cannot reuse a previous pipeline result. The Docker driver selects at most eight available VM CPUs, matching affinity, OpenMP, and model threads, while retaining the 6-GiB memory cap and isolated loopback namespace. A single test cannot isolate every source of latency.

Direct Tesseract text output contained the extra space too; the TSV reader was not its source. Switching segmentation mode alone did not remove the error. Two-times Lanczos scaling recovered `python agent.py` from the original compressed frame under Debian Tesseract 5.3. The OCR stage now scales its temporary input at most two times, capped at 3840 by 2160 for supported source dimensions. It keeps the original frame and recognized text unchanged. Large source frames are not downscaled. Temporary files are removed even on failure. This is a new extraction version, not a repair of old evidence.

The pixel-scaling approach follows [Tesseract's image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html). It does not establish general OCR accuracy: fixture results are development evidence, and punctuation, spaces, symbols, and uncertain text still require human source review. The raw 2x probe still fragmented parts of the assignment line; exact command success is not whole-frame fidelity.

## Checks

96 tests passed with zero skips in the normal user environment. Regression checks cover source bytes remaining unchanged, preprocessing size bounds, temporary-file cleanup, native English OCR, preservation of literal `agent. py` when that is the recognizer output, invalid thread limits, and propagation of the thread limit to the model request. The independent container extraction check passed both structural validation and exact-command fidelity on the compressed video frame.

## Full model result

`./scripts/check-docker.ps1` built the image and returned exit 0. Session: `outputs/docker-check/run-8982b6fbf4`. Job: `5f5c3321b08cfde15efdbc06b9498f5202d23bf30e1eb06abdb7eee0f81fe658`. Both attempts passed the unchanged schema and semantic validator, exported Markdown, and had audio, OCR, and vision available. OCR contained the exact `python agent.py` line. The independent verifier accepted both structural and exact-command checks.

| Stage | First attempt, seconds | Replay |
| --- | ---: | --- |
| Probe | 0.077 | Cached |
| Frames | 0.585 | Cached |
| ASR | 5.731 | Cached |
| OCR | 0.390 | Cached |
| Vision | 120.556 | Cached |
| Synthesis | 211.144 | Cached |
| Pipeline | 338.590 | 0.107 seconds |

First attempt: 3335 input tokens, 630 output tokens. Replay: zero new tokens, all stages successful and cached. Each call stayed within the original 300-second timeout. There were no model retries or schema repairs. Actual API cost and paid cash were zero. Logs confirm eight inference and batch threads for both models, and no OOM kill was recorded. The temporary model server was stopped and removed; final `docker ps` showed no running containers. Image ID: `sha256:65c3802bc0fce73b0fb2bf80ab18a67b3f79a80f4221d959e7da6cb3f858f51a`.

Outputs correctly remain partial: OCR fragments the assignment's symbols, ASR mishears retries as entries, and source uncertainty survives into Markdown. This establishes full synthetic wiring and cache behavior, not general tutorial accuracy. Timings are single observations under different system load, not a controlled native-versus-container benchmark. Real clips and human source review remain outstanding.

Final verification: 96 tests passed, zero skips; PowerShell parsing passed; independent read-only code review found no material regression; implementation diff/whitespace checks passed. Docker remains optional. Native execution does not need Docker, and Docker does not replace real-video acceptance.
