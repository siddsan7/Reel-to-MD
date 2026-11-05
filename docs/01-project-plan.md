# Project plan and decisions

## Objective

Create useful notes from short AI and agent tutorials while demonstrating research and applied ML engineering judgment. The working hypothesis is that supervised fine-tuning improves important-fact recall over a strong prompted version of the same model, without increasing unsupported claims, when both receive identical extracted evidence.

Success includes knowing when not to train. If failures originate in missing or incorrect extraction, improve that stage before expanding synthesis training.

## Scope

Initial scope: English tutorials, Android intake, Instagram links where retrievable, and direct video upload. Pilot clips are 30 to 120 seconds. Preserve transcript and visual evidence references. Output structured notes and a Markdown export, optionally bundled with selected screenshots.

Exclude from version one: foundation-model pretraining, end-to-end audiovisual training, autonomous execution of extracted commands, external fact-checking, generated next-step suggestions, multilingual claims, unrestricted web-video support, and on-device training. Android is the client; model computation can be remote.

## Research framing

Distinguish input grounding, fidelity to the original video, and external factual truth. A grounded response can repeat an OCR error. A faithful response can reproduce a false creator claim. Measure the first two separately and attribute creator claims.

The portfolio targets research/post-training engineering and applied ML roles. Demonstrate an annotation protocol, controlled experiments, error analysis, cost accounting, reproducibility, and a usable system. A small pilot does not establish production reliability or research novelty.

## Milestones

The eight-week outline assumes approximately 15 to 20 hours per week and comfortable Python skills. It is a planning estimate, not a deadline.

| Stage | Work | Exit evidence |
| --- | --- | --- |
| Week 1 | 20-clip pilot, share feasibility, schemas | Pilot report with measured bottlenecks and costs |
| Week 2 | Approximately 50 diagnostic examples and strong baseline | Stable annotation rules and training hypothesis |
| Weeks 3 and 4 | Curated data and first SFT | Reproducible baseline versus SFT results |
| Week 5 | Error-driven data improvements and ablations | Explanation of what caused gains or failures |
| Week 6 | Conditional preference experiment or better data | Evidence for using or rejecting DPO |
| Week 7 | Android integration and operations | End-to-end tests, spending controls, rollback |
| Week 8 | Frozen evaluation and publication package | Results, limitations, model/data cards, reviewed demo |

Scale toward approximately 200 training, 25 validation, and 50 untouched final-test clips from a larger candidate pool. These counts are targets, not guarantees of adequate statistical power. The 20 pilot clips are development data and never become the final test set.

## Decision register

| Decision | Rationale | Reconsider when |
| --- | --- | --- |
| Fixed extraction followed by text synthesis | Isolates a trainable behavior within the budget | Visual errors dominate and text descriptions cannot preserve needed evidence |
| Evidence-linked JSON before Markdown | Separates content quality from formatting | User workflow needs another representation |
| QLoRA on a 4B instruction model | Small, controlled adaptation experiment | Profiling exceeds budget or capacity is demonstrably insufficient |
| Teacher-assisted labels with review | Reduces drafting effort without treating generated labels as truth | Correction rate makes this slower than manual annotation |
| SFT before DPO | Establishes a clear baseline and simpler intervention | Persistent errors have reliably rankable preferred alternatives |
| No RL initially | No reliable reward has been established | A verifiable objective and clear advantage over simpler methods emerge |
| No automatic learning from user corrections | Prevents silent dataset contamination | A consented review and versioning process exists |

Initial candidates are not claims of superiority. Pin exact revisions before experiments.

## Responsibilities and release

The project owner supplies or selects source material, resolves annotation ambiguity, and reviews consequential scope changes. Engineering work can automate intake bookkeeping, extraction, drafting, validation, scoring, and reports. A second reviewer is useful for a small annotation subset; disclose if unavailable.

Merges, deployments, and publication require review by the user or an explicitly assigned reviewer. Documentation does not authorize paid service purchases or publication of source media. Honor the agreed cash ceiling and account access constraints.

## Primary references

- [Qwen text model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Qwen vision model family](https://github.com/QwenLM/Qwen3-VL)
- [Teacher-generated data precedent](https://arxiv.org/abs/2212.10560)
