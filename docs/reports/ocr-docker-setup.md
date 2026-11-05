# OCR and Docker setup

Historical setup results. The timeouts and exact-command spacing failure below were subsequently resolved for the synthetic fixture; see [container fixes and successful full check](docker-fixes.md). Original failures remain preserved.

Date: 19 October 2026. Scope: user-authorized native OCR installation, synthetic pipeline rerun, and local Docker setup/testing. No paid APIs, rented GPUs, real clips, training, publication, or deployment.

## Native OCR

Installed verified WinGet package `UB-Mannheim.TesseractOCR` 5.4.0.20240606 for the current user. English and OSD language data are available. The pipeline now discovers standard Windows install locations without editing global PATH; `TESSERACT_CMD` can override the executable. Version probes use Tesseract's supported `--version` flag. OCR explicitly selects English.

88 tests passed in the normal user environment, including live OCR of an exact command and timestamp. In the restricted shell, user application discovery sees a sandboxed LOCALAPPDATA and the native OCR test skips; that was not treated as verification. The normal user test run had no skips.

The live generated-video pipeline passed the unchanged evidence/target validator and exported Markdown with audio, OCR, and vision all available. The six-second clip is synthetic. Original source inaccuracies remain: Whisper misheard retries as retrieves; sparse-text OCR fragmented parts of `max_retries = 3`. OCR and vision were flagged uncertain. The exact `python agent.py` line was recovered by native OCR. No source text was repaired.

| Stage | First attempt, seconds | Replay |
| --- | ---: | --- |
| Probe | 0.079 | Cached |
| Frames | 0.375 | Cached |
| ASR | 4.531 | Cached |
| OCR | 0.234 | Cached |
| Vision | 64.844 | Cached |
| Synthesis | 151.453 | Cached |
| Pipeline | 221.547 | 0.094 seconds |

First attempt: 3352 model input tokens, 717 output tokens. Replay: zero new tokens, all stages cached. Measured pipeline time excludes startup/model hashing and coincided with Docker's first startup; this is not a controlled speed comparison. Native report: `outputs/native-ocr-summary.json`; job `5de230fb2790ae26a7e3416116a4a20ed50669a3af141d501dc4f5f4621cd799`.

## Docker installation and build

Installed Docker Desktop 4.95.0 per-user with the local WSL 2 backend and Linux containers. Existing WSL 3.0.3 was available. No reboot, WSL reset, Ubuntu termination, Windows-container setup, or paid plan was used. Local engine: Linux Docker 29.8.2, 16 reported CPUs, about 7.76 GiB VM memory.

Initial engine API requests failed while first boot was still starting; the engine then became ready. The first image build failed because this shell predates installation and could not find `docker-credential-desktop`. Adding Docker's installed binary directory only to that process's PATH resolved it. The local image then built successfully with no remote builder or push.

Image checks passed with networking disabled and a read-only filesystem: nonroot UID 10001; faster-whisper 1.2.1; PyAV 18.1.0; packaged schemas/prompt; English OCR; synthetic JSON validation and Markdown export; actual ASR/OCR extraction of the generated video with read-only weights/input and writable output mounts.

Debian Tesseract 5.3.0 produced `python agent. py` from the compressed frame. Its evidence remained uncertain. The exact-command fidelity assertion failed, separately from successful structural validation and channel availability. This demonstrates why a container test must report source accuracy separately from successful execution.

## Isolated model test design

Automatic approval review rejected a proposed persistent Docker host-network change because it reduces network isolation and was not explicitly authorized as a security-setting change. Nothing from that command was applied. The implementation used a safer alternative: an unprivileged official Ollama container with `--network none`, no ports, a read-only model-only mount, cloud features disabled, no added capabilities, and no new privileges. The pipeline joins only that isolated network namespace, retaining `127.0.0.1` validation without reaching host services. No host networking or Docker socket mount is used.

Official Ollama image: `ollama/ollama:0.40.3`, repository digest `sha256:adca95a12c2b386a8f9a995e7fa0600e187e3323b5e5522f5a6c3b1ec73eff99`. The same downloaded Qwen weights are reused read-only. The server is capped at 8 CPU equivalents and 6 GiB memory. This resource profile differs from native testing.

The driver retains original outputs, checks required channels/validation/cache replay, records OCR fidelity separately, saves server logs/exit/OOM state, and removes only its generated server container. See [setup and test commands](../10-local-models.md).

## Full container outcome

`./scripts/check-docker.ps1 -SkipBuild` returned exit 1 as required. Session artifacts are in `outputs/docker-check/run-628bfcc330`. The fresh extraction pass took 6.954 seconds and passed structural checks; exact OCR command fidelity failed as described above.

The full model attempt took 608.717 seconds. ASR and OCR succeeded; vision timed out after 300.518 seconds and synthesis timed out after 300.471 seconds. Target validation was not reached. No Markdown export or model cache replay was accepted. The driver stopped on the failed CLI status, so it did not attempt the replay. Token counts for incomplete calls are unknown, not zero. Paid cash and model API cost were zero. No timeout, context limit, or validator was weakened to pass.

The saved server snapshot showed it still running, `OOMKilled: false`, and no published ports. Logs show CPU inference progress, but do not establish a single cause for the timeouts. The 8-CPU/6-GiB container cap, WSL VM limits, and runtime differences were not isolated experimentally. After logs/state were saved, the generated server was stopped and removed; `docker ps` showed no running test containers. Docker Desktop remains installed and running. Persistent host-network settings remain unchanged.

Use the native workflow for full model inference on this laptop. Docker is useful for repeatable dependency packaging and offline extraction; this CPU profile has not passed the full Qwen workflow. Real clips and human source review remain necessary. No real-video quality claim is supported by these synthetic checks.

Final checks: 88 tests passed with zero skips; PowerShell driver parsing and Python script compilation passed; implementation diff inspection found no whitespace errors. The Docker runtime failures are retained as failures, separate from those checks.
