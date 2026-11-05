# Local models and optional Docker

Date: 19 October 2026. No paid APIs, rented GPUs, or real source clips are required for this setup.

## Native setup

The Windows laptop has a Core Ultra 9 285H, about 32 GB RAM, and Intel Arc 140T integrated graphics. Use CPU ASR and native Ollama. Run stages in sequence. The Ollama adapter unloads weights after each request with `keep_alive: 0`; it does not keep vision and synthesis models resident together.

The selected models are:

| Stage | Model | Installed revision |
| --- | --- | --- |
| ASR | `Systran/faster-whisper-small.en`, CTranslate2 | `d1d751a5f8271d482d14ca55d9e2deeebbae577f` |
| Vision | `qwen3-vl:4b-instruct`, Q4_K_M | `ee4b975b58c17ce268cd19d40db35d5edc64603035d2ffc1fee1968eb0947f7b` |
| Synthesis | `qwen3:4b-instruct-2507-q4_K_M`, Q4_K_M | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |

Start your existing Ollama application. Then, from the repository root:

```powershell
./scripts/setup-local.ps1
.venv/Scripts/reel-to-md run data/private/development/code.mp4 --config data/private/local-config.json
```

Setup downloads the two explicit Ollama tags and a pinned Whisper revision. It writes `data/private/local-config.json` using the full installed Ollama digests. Later setup runs can obtain a newer tag; compare the recorded digest before accepting a model update for an experiment. Inference checks the configured digest against installed local weights before each new request. A changed or missing model is rejected. It never pulls a model, contacts a hosted endpoint, or executes extracted commands.

Whisper weights live in ignored `models/whisper-small.en`. Ollama manages its weights in its own store. Do not copy these into Git or Docker images. Setup requires internet access to public registries; inference uses existing local files and a literal loopback endpoint. No API credentials are required.

The locked optional ASR environment includes a compatibility bound `av<19`. The first live test found that faster-whisper 1.2.1 calls `av.open(metadata_errors=...)`, which PyAV 19 removed. PyAV 18.1.0 is the tested locked version. Do not remove the bound without running the decoder regression and live ASR check.

The native Ollama adapter uses `/api/chat`, schema-constrained synthesis, thinking disabled, an 8192-token context, at most 2048 generated tokens, and a 300-second request timeout. It sets `truncate: false` and `shift: false`: evidence must fit the context or fail visibly. These settings are configurable within bounded limits. A live negative check on Ollama 0.40.3 rejected a 15009-token synthetic request in a 2048-token context with HTTP 400. Large real packets still need capacity evaluation. The generic OpenAI-compatible adapter remains available with `model_backend: "openai"`.

Before synthesis, the output schema is narrowed to actual evidence IDs and possible source attribution. For this conservative local baseline, only normal OCR lines are eligible for the exact command field; spoken instructions remain prose. Packet-derived uncertainty and missing-channel entries are mandatory in the generation schema. This is a generation constraint; no response is repaired afterward. The full original schema and semantic validator still check the result. The Ollama server version is recorded and included in cache identity, along with weight digests and package versions.

Real-packet capacity: the first flowchart request measured 10,956 tokens and exceeded the default 8,192-token context. Synthesis now sends compact UTF-8 evidence and avoids repeating its decoding schema in the prompt. The separate 32-GB laptop profile `data/private/local-config-real-v2.json` uses `context_tokens: 16384`, `output_tokens: 2048`, `model_timeout_seconds: 600`, and `ollama_threads: 8`. This preserves all evidence and creates a new job identity; it is not a universal profile for smaller systems. Run with `--config data/private/local-config-real-v2.json`. See [real synthesis diagnosis and reruns](reports/real-synthesis-fix.md). HTTP rejections retain bounded, redacted `*.error.json` diagnostics in the private model cache; pending markers still block automatic repeat dispatch.

The denser flowchart packet continued beyond 600 seconds on this CPU. `data/private/local-config-real-v4.json` keeps that profile's model settings and explicitly selects a 1,200-second request deadline. The configurable ceiling is 1,200; the default remains 300. Run with `--config data/private/local-config-real-v4.json` for this longer local CPU budget. No automatic retry, silent truncation, or validator relaxation is enabled. Large packets can still fail their bounded limits; retained error diagnostics distinguish transport/context failures from invalid drafts.

FFmpeg/ffprobe must be on PATH. Tesseract 5.4.0.20240606 is now installed for the current Windows user with English and orientation data. The pipeline checks PATH, `TESSERACT_CMD`, and standard Windows install locations; no global PATH edit is needed. The Docker image includes Debian Tesseract 5.3.0. Vision reports are never relabeled as OCR. Different engine/data versions can produce different OCR; preserve uncertainty and review source fidelity.

References: [Ollama chat API](https://docs.ollama.com/api/chat), [schema-constrained output](https://docs.ollama.com/capabilities/structured-outputs), [Whisper weights](https://huggingface.co/Systran/faster-whisper-small.en).

## Checks without real clips

```powershell
$testTempPath = Join-Path (Get-Location) ('work/pytest-' + [guid]::NewGuid().ToString('N'))
.venv/Scripts/python -m pytest -q --basetemp=$testTempPath
.venv/Scripts/python scripts/check-local.py
.venv/Scripts/python scripts/check-local.py --require-ocr
.venv/Scripts/python scripts/check-context-limit.py
```

The live checker needs FFmpeg's `flite` speech filter, which is available in this machine's FFmpeg build. It generates known speech and a readable static terminal screen, then runs the actual ASR, vision, synthesis, validation, and renderer. A second attempt checks cache reuse without new model tokens. It writes a synthetic summary to `outputs/local-smoke-summary.json` and retains each attempt's original response, target, evidence, notes, and run record. These are wiring checks, not real-video quality results. The checker exits nonzero if ASR/vision evidence, schema/semantic validation, basic source strings, or cache replay fail. Missing OCR remains explicit.

The earlier model-only check passed in 156.250 seconds with OCR unavailable. After installing Tesseract, all three channels were available, validation passed, and the measured pipeline took 221.547 seconds; replay took 0.094 seconds with zero new model tokens. Source uncertainty still makes the notes partial. These single-job timings exclude startup/version hashing and ran under different system load; they are not a performance comparison. See [earlier model results](reports/local-model-setup.md) and [OCR/Docker results](reports/ocr-docker-setup.md).

No regeneration or silent output repair occurs. Failed first passes remain private artifacts under their original versioned job. Prompt changes produce a new job identity. ASR may mishear synthetic speech; compare the evidence with `work/local-smoke/speech.txt` rather than treating extraction as ground truth.

## Why Docker is optional

Docker packages Python, FFmpeg, Tesseract, and Linux libraries together. This reduces setup differences across machines. It does not make CPU speed, GPU drivers, model quality, or memory identical. For this Windows laptop, native Ollama is already working; installing Docker Desktop is not required to use the pipeline.

`Dockerfile` provides a CPU pipeline image with the locked ASR environment, English OCR, and packaged contracts. `.dockerignore` uses an allowlist so private media, weights, outputs, caches, credentials, and Git metadata are excluded. The image runs as an unprivileged user. Build requires registry/package downloads; runtime can use local weights offline. Base-image tags and apt security updates are not a bit-for-bit operating-system lock.

Docker Desktop 4.95.0 and its local Linux engine 29.8.2 are installed and running through the existing WSL 2 installation. No Windows reboot was needed. The image builds locally. Nonroot/read-only/offline JSON, ASR, and OCR checks have run. This is a local test environment, not a deployed service.

Build and perform a network-disabled synthetic JSON check:

```powershell
docker build -t reel-to-md:local .
New-Item -ItemType Directory -Force outputs/docker | Out-Null
docker run --rm --network none --read-only --tmpfs /tmp --mount "type=bind,source=$((Get-Location).Path)/outputs/docker,target=/outputs" reel-to-md:local check-example /app/example.json --output /outputs/check
```

For reproducible checks of the full pipeline on Windows:

```powershell
./scripts/check-docker.ps1 -SkipBuild
```

The script starts the official versioned `ollama/ollama:0.40.3` image with networking disabled, CPU only, a read-only local model-store mount, an unprivileged user, no capabilities, and no published ports. The pipeline container joins only that container's network namespace (`--network container:<test-server>`). Its `127.0.0.1` reaches the isolated model server, not host services. Ollama cloud features are disabled. Input/ASR mounts are read-only; output is writable. The temporary server's logs/state are saved before it is stopped and removed. The existing native Ollama service and Ubuntu WSL distribution are left intact.

This avoids persistent host-network settings and preserves the literal-loopback endpoint rule. A proposed host-network change was declined by automatic approval review because it reduces isolation; it was not applied. No endpoint allowlist was weakened. See [Docker network namespace sharing](https://docs.docker.com/reference/cli/docker/container/run/#network).

Each test invocation uses a fresh output directory under `outputs/docker-check/run-*`. `verify-docker.py` checks actual records and evidence rather than trusting a zero CLI exit: partial jobs can have failed channels. Structural success, source-string fidelity, and cache reuse are separate results. A fidelity failure returns a nonzero check status even when the pipeline exports valid partial notes; no OCR string is normalized to pass. Earlier Debian OCR inserted a space in `python agent. py`. Bounded 2x image scaling now recovers the exact command in the compressed fixture, while preserving original source frames and literal recognizer output. Other OCR errors remain possible.

The initial full Docker model test timed out with 16 model threads under an eight-CPU quota. Affinity alone did not change the runtime's thread choice. The driver now explicitly sets `ollama_threads` to at most eight available VM CPUs and matches CPU affinity. Native configuration can omit this field for automatic thread choice. Explicit values must be integers from 1 to 64 and are part of job identity. Keep the chosen thread count within your CPU allocation.

The corrected full test passed with the same models, 6-GiB server memory cap, context/output limits, 300-second call timeout, and validators: vision 120.556 seconds, synthesis 211.144 seconds, total 338.590 seconds. Replay took 0.107 seconds with all stages cached and zero new model tokens. See [fixed container results](reports/docker-fixes.md) and [preserved initial failures](reports/ocr-docker-setup.md). Both native and Docker execution remain supported; real-video quality acceptance is still pending.

For Linux bind mounts, the output directory must be writable by UID 10001, or run with your user's UID/GID. The image is portable; the PowerShell test driver is for Windows. Keep real media and outputs private, and review model/source fidelity before using exports as technical instructions.


Real-clip synthesis uses compact, lossless packet messages and a separately supplied decoding schema. Mandatory uncertainty entries use fixed tuples compatible with the installed local decoder; exact commands are bound to one normal OCR source. These generation restrictions preserve the original semantic validator. See [real synthesis repair](reports/real-synthesis-fix.md) for measured failures, explicit CPU profiles, and current review results. The 1,200-second maximum is optional; the default remains 300 seconds. The current repair is tested natively; its real-clip container run has not been repeated.


Setup also writes a separate `data/private/local-ui-config.json` with the measured real-clip CPU resource settings. Start `./scripts/start-ui.ps1` to use it in the [local upload, review, export, and recovery workspace](12-local-ui.md). The standard configuration remains separate.
