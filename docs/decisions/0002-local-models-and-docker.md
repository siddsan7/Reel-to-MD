# Decision record: local models and optional Docker

Status: accepted for local implementation. Date: 19 October 2026. Owner: implementation agent under the user's explicit request.

## Goal, constraints, and acceptance

Install Whisper small.en, Qwen3-VL-4B-Instruct, and Qwen3-4B-Instruct-2507. Run local inference without paid APIs, GPU rentals, real clips, model training, or deployment. Verify weights, timestamped synthetic speech, visible source text, validated model notes, repeated-job caching, and failure behavior. Keep model weights and generated outputs out of Git.

## Choices and evidence

Use the existing native Ollama installation for the two Qwen models and CPU int8 faster-whisper for ASR. Setup explicitly downloads weights; inference does not. Check installed model digests before dispatch, include runtime versions in job identity, bound context/output, disable input truncation/context shifting, and unload Ollama weights after each call. This limits simultaneous memory use on the 32 GB laptop.

The first real ASR attempt reproduced a faster-whisper/PyAV API mismatch. Constrain PyAV below 19 and add a real WAV decoder regression. Preserve the observed synthetic transcription error (retries -> retrieves).

Two live synthesis attempts returned JSON that failed semantic validation. The second repeated wrong attribution and invented a channel name as an evidence ID. Stop prompt-only iteration. Narrow the generation schema using packet IDs, available attribution kinds, exact supported command strings, and packet completeness. A subsequent constrained attempt corrected IDs and attribution but omitted the uncertain vision reference and copied a transcript sentence into the command field. Make packet-derived uncertainty entries mandatory during decoding, and restrict exact-command candidates to normal OCR lines for this local baseline. Spoken instructions remain prose. Keep the original validator unchanged and retain every failed target. This also applies to future clips; it is not a synthetic-specific replacement target.

## Docker scope

Provide an optional CPU image for Python, FFmpeg, Tesseract, and the locked ASR environment. Use an allowlisted build context, nonroot runtime, mounted weights, and offline inference settings. Keep native Ollama outside the image; use explicitly enabled host networking to preserve the loopback-only endpoint policy. Do not install Docker Desktop or change system networking as part of the model setup. Docker is unavailable here, so the image remains unbuilt and requires later review/testing.

## Reversal conditions

Choose larger models or GPUs only after real development clips show a need. Revisit context limits after measuring real evidence size. Remove the PyAV bound only after an upstream compatibility change passes the decoder and live ASR checks. Update model digests only as an intentional experiment version. Treat Docker as optional until image build, permissions, and host connectivity pass on a Docker-equipped system.
