# Evaluation protocol

## Evaluation stages

The 20-clip pilot is a development study. Use 12 clips to improve prompts and eight creator-disjoint clips for a one-time diagnostic audit. Freeze versions before the audit. After opening audit results, all 20 remain development data; none becomes the final test set.

The later study targets 200 train, 25 validation, and 50 new untouched test clips. Deduplicate and split by source group first. A separate challenge set exercises deliberate failure cases and is reported separately.

## Ground truth and denominators

For every reference fact, annotate importance, source support, and availability in model input. The synthesis metric uses source-supported facts recoverable from input; the end-to-end metric uses all source-supported facts. Separately label erroneous extracted claims: repeating incorrect OCR can be input-grounded while still being a source-fidelity error. Contradictory evidence can support an attributed conflict, but not a confident resolution.

Score outputs as atomic factual claims. Count title assertions and procedural commands as claims when factual. Match semantically rather than by surface wording. Record omissions, partial support, unsupported additions, incorrect source attribution, and evidence-link errors.

| Metric | Definition |
| --- | --- |
| Synthesis recall | Correct important source-supported reference facts recovered divided by source-supported important facts recoverable from input |
| End-to-end recall | Correct important source facts recovered divided by important facts in video |
| Unsupported claim rate | Output claims without full input support divided by output factual claims |
| Source error rate | Output claims inconsistent with original video divided by output factual claims |
| Citation support precision | Supporting claim-to-evidence links divided by all asserted links |
| Reference validity | Existing referenced IDs divided by all referenced IDs |
| Technical item accuracy | Exactly correct required technical items recovered divided by required available items |
| Conflict recall | Correctly represented conflicts divided by annotated conflicts |
| Uncertainty recall | Correctly flagged material gaps divided by annotated material gaps |
| Unnecessary uncertainty | Answerable items incorrectly marked unknown divided by answerable items |
| First-pass validity | Schema-valid first responses divided by attempted synthesis requests |
| Export success | Valid delivered exports divided by all accepted jobs |

A zero denominator is N/A, not perfect performance. Report counts, macro averages over eligible clips, and micro totals. Empty answers have zero recall when facts are available; do not celebrate their undefined unsupported-claim rate.

Exact technical comparison preserves case, punctuation, flags, numbers, and units. Permit only explicitly documented whitespace normalization. Partial technical strings do not count as exact.

## Human review and judges

Blind model identities and randomize comparison order. Human-verify test references against both video and extracted evidence. A teacher output is not a reference until reviewed.

Use an LLM judge only for triage or supplementary analysis. Calibrate against human labels; inspect false acceptances and false rejections. For pairwise judging, swap order and check sensitivity. Disclose shared teacher/judge families. [Research documents position and verbosity biases](https://arxiv.org/abs/2306.05685).

Use paired clip comparisons. If multiple clips share a creator/series, bootstrap by source group, carrying its clips together. Report 95 percent intervals, source-group counts, and raw counts. Tiny pilot groups support descriptive findings only. Do not treat many claims from one clip as independent evidence.

## Predefined slices and challenge cases

Report by visual format, visual-only facts, exact-code content, noise/blur, conflicts, missing channels, and seen/unseen topics where supported. Small slices get counts rather than broad conclusions.

Challenge fixtures cover injected instructions in OCR/audio, fabricated URLs, credentials, invalid evidence IDs, missing timestamps, truncation, absent modalities, corrupted media, inaccessible links, and renderer injection. Synthetic fixtures are not natural clips and do not expand the independent sample count.

## Proposed full-study gates

Freeze final numerical gates after the pilot and before final training/test inspection. The following are initial product preferences, not validated standards:

- At least 5 percentage points higher synthesis recall than B1.
- No observed increase in unsupported-claim rate.
- Report intervals and do not claim established superiority when uncertainty includes no gain.
- No known fabricated executable command, credential disclosure, or instruction-following escape in the declared challenge suite.
- Every released export passes schema/reference/render checks; failures remain explicit and count against export success.
- Cost stays within the recorded job and experiment limits.

Zero observed severe failures is a release condition for this suite, not a claim of universal safety. A failure triggers remediation and rerun of affected tests. Any test used to tune the model becomes development evidence.

## Downstream utility

After the primary extraction study, use a fixed separate agent to answer source-specific questions from notes only, with tools/web disabled. Score evidence-cited answers against human references. Compare against an empty-notes control to expose answers from prior knowledge. Treat this as secondary utility evidence, not a replacement for extraction evaluation.

## Reporting

Include baseline and SFT results, paired deltas, intervals, slice counts, first-pass and repaired outcomes separately, p50/p95 stage latency, cost per attempt and per successful export, annotation time, error taxonomy, representative wins/regressions, and excluded examples.

Use [clip scores](templates/clip-scores.csv) and [pilot report](templates/pilot-report.md). No benchmark results are populated in this package.
