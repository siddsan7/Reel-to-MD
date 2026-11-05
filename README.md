# Reel to MD

Turn short educational videos into evidence-grounded Markdown using timestamped transcription, OCR, and visual descriptions. The research goal is to test whether post-training a compact text model improves synthesis over a strong prompted baseline.

## Start here

- [Documentation index](docs/README.md): full plan, architecture, data protocol, training, guardrails, evaluation, and budget.
- [20 clip pilot runbook](docs/08-pilot.md): sample selection and execution order.

The implementation includes a Python CLI, local extraction/model adapters, versioned validation, safe Markdown, caching, run records. Native and container synthetic model checks pass. Real-video acceptance and trained weights remain pending. See [setup and usage](docs/09-local-pipeline.md) and [local review and evaluation](docs/11-review-evaluation.md).

```powershell
python -m uv sync --locked
.venv/Scripts/reel-to-md check-example docs/examples/example.json
.venv/Scripts/reel-to-md run path/to/local-video.mp4
```

The example is a synthetic wiring check. Video jobs use FFmpeg/ffprobe, optional Tesseract and local ASR weights; unavailable channels are explicit. Without a configured synthesis model, exports are conservative extractive drafts requiring review. No API keys are needed, and hosted inference is disabled.

To use the selected local models on Windows, run `./scripts/setup-local.ps1`, then pass `--config data/private/local-config.json` to `run`. See [local models and optional Docker](docs/10-local-models.md). Native execution and the full Docker CPU pipeline have passed synthetic workflow and cache checks. Docker uses bounded OCR scaling and explicit model threads; see the [measured results](docs/reports/docker-fixes.md). Native setup works independently.

## Initial direction

- Android and Instagram first, with video upload as the development path.
- Fixed transcription, OCR, and visual extraction followed by text synthesis.
- Qwen3-4B-Instruct-2507 with QLoRA is the initial training candidate; profile before committing compute.
- Begin with two development clips, then the 20-clip pilot.
- Target USD 30 total initial spending; ceiling USD 40, including a pilot allocation of at most USD 5. These are limits, not measured cost estimates or spending authorization.

Keep private media, filled research records, model outputs, and credentials in ignored locations. The files under docs/templates are blank reusable templates; copy them into data/private before filling them with source information. Git ignore rules prevent accidental tracking, not unauthorized filesystem access.

The repository documentation is the implementation reference.
