# Reel to Markdown project documentation

Version 0.1 · 18 October 2026 · Planning baseline

Build an Android application that accepts an Instagram reel link or an uploaded video and exports evidence-grounded Markdown for a human and an agent to work through together. The research contribution is post-training a compact text model to synthesize timestamped transcription, OCR, and visual descriptions.

The plan below is the original research baseline. The current implementation includes a local CLI and evidence pipeline. Two real development clips have validated draft notes; human factual review remains pending. Models have not been trained. See the [bound excerpt report](reports/excerpt-grounding-fix.md) for verified results.

## Reading order

1. [Project plan and decisions](01-project-plan.md)
2. [Architecture and output contract](02-architecture.md)
3. [Data collection and annotation](03-data-protocol.md)
4. [Training and experiments](04-training.md)
5. [Evaluation protocol](05-evaluation.md)
6. [Guardrails and operations](06-guardrails.md)
7. [Budget and resource plan](07-budget.md)
8. [20 clip pilot runbook](08-pilot.md)
9. [Local pipeline setup](09-local-pipeline.md)
10. [Local models and optional Docker](10-local-models.md)
11. [Bound excerpt drafting and Windows persistence fix](reports/excerpt-grounding-fix.md)

## Working templates

- [20 clip intake manifest](templates/clip-intake.csv)
- [Fact annotation sheet](templates/fact-annotations.csv)
- [Per clip scorecard](templates/clip-scores.csv)
- [Cost ledger](templates/cost-ledger.csv)
- [Experiment record](templates/experiment-record.md)
- [Decision record](templates/decision-record.md)
- [Pilot report](templates/pilot-report.md)
- [Teacher prompt](templates/teacher-prompt.txt)
- [Review prompt](templates/reviewer-prompt.txt)
- [Evidence packet schema](schemas/evidence.schema.json)
- [Target output schema](schemas/target.schema.json)
- [Synthetic example](examples/example.json)

The intake manifest has 20 planned slots, not collected videos. The example is synthetic and must not be counted as real training or evaluation data. The schemas define the interface; the implementation includes semantic validation, safe rendering, and local job controls.

## Project status

| Item | Status |
| --- | --- |
| Android and Instagram first | Product direction |
| Text synthesis with fixed extractors | Initial architecture |
| Qwen3-4B-Instruct-2507 with QLoRA | Initial training candidate |
| Qwen3-VL-8B-Instruct and Gemini 3.1 Flash-Lite | Extraction comparison candidates |
| Stronger teacher model | To select using reviewed pilot examples |
| Total initial cash ceiling | USD 40; aim to finish within USD 30 |
| Pilot training | Optional plumbing check only |
| Quality thresholds | Proposed; freeze after pilot and before final study |
| Application and pipelines | Local CLI implemented; human real-video acceptance pending |
| Public release | Requires user or assigned reviewer review |

Use the local documents as the detailed working reference. Update the version and decision record when the plan changes materially.
