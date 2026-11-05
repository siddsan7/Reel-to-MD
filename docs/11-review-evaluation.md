# Local review and development evaluation

This workflow needs no API keys, model calls, web server, or new Python dependencies. Open a generated HTML file in your own browser, annotate locally, and finalize with the CLI. Original attempts are never rewritten. Private review bundles include source text and images; keep them in ignored `outputs/` or `data/private/` directories.

## Create a review

First process the video with the normal pipeline. Use the printed **attempt directory**, not the parent job directory:

```powershell
.venv/Scripts/reel-to-md review-init outputs/jobs/JOB/attempts/ATTEMPT --video data/private/clip-01.mp4 --output outputs/reviews/clip-01
```

Open `outputs/reviews/clip-01/review.html` in a local browser. The page contains the original evidence, selected frames, structured output, and source-video player. No remote assets, source links, HTML from evidence, or external requests are executed. Some video codecs need a separate local player. Closing the page loses unsaved changes; download annotations regularly.

`source.json` binds the source snapshot to original file hashes. `review.json` is a pending annotation template. Images and optional video are copied into `assets/`. New pipeline records contain `input_sha256` and `input_kind`, including on failed jobs. A supplied video must match that hash when available. Legacy runs without an input hash require manual source/attempt identity confirmation. Natural-clip finalization requires a copied, hashed video. Legacy attempts with no reliable input classification cannot be finalized; create an explicitly classified pipeline attempt instead.

## Review against the video

1. Enter a reviewer, stable clip key, creator/source group, condition, and review time. Use the same clip key across conditions for the same video. Condition is a manual experiment label; this command does not run B0/B1/T0 or ablations.
2. Watch the original video. Distinguish original-video facts from what survived into the extracted evidence. Confirm the source belongs to the attempt; reading the model's notes is not source verification.
3. Review every output text field, including title assertions, steps, command strings, conflicts, and uncertainty text. Select an assertion in its read-only text box and choose **Split selected assertion** when a field contains multiple facts. New units require new judgments, and fact matches to a removed unit ID must be remapped.
4. For each factual unit, label full/partial/no input support, correctness against the original video, and support for each original citation. These are separate judgments: copying wrong OCR can be input-supported but source-incorrect. A nonfactual exclusion needs a reason. Do not mark assertions nonfactual just because they are wrong.
5. Add the complete reference fact inventory, including omitted facts. Mark importance, source support, and input availability independently. Match recovered facts to output unit IDs. Each reference fact counts once. For technical items, enter the exact expected string and match a unit containing exactly that observed technical string. There is **no whitespace, case, punctuation, flag, number, or unit normalization**.
6. Add reference conflicts and material gaps. Mark whether the original output represents each correctly and identify its output field paths, such as `/conflicts/0/text` or `/unknowns/0/text`. Empty inventories mean there are no such reference items, not that annotation was skipped. Answerable source facts also require a judgment on unnecessary uncertainty.
7. Confirm coverage and inventory completeness. Atomic units use literal Unicode code-point spans of original fields; every non-whitespace character, including operators and punctuation, must be covered. The advanced JSON editor supports manual changes. Human judgment must still establish atomicity and semantic truth.
8. Choose accept, edit, or reject. For an edit, change the structured target in the final editor. Existing evidence, references, exact-command support, and uncertainty rules still apply. Correcting an extraction itself requires a separate pipeline/evidence revision; this editor does not relabel source evidence.

All semantic labels start pending. The page does not automatically judge or approve content. Downloading an annotation file does not finalize it. You can resume by importing that file into the same page; review ID and source digest must match.

## Finalize a separate revision

Copy the downloaded annotations beside `source.json`, for example as `annotations.json`:

```powershell
.venv/Scripts/reel-to-md review-finalize outputs/reviews/clip-01/annotations.json --output outputs/reviews/clip-01-final-v1
```

Finalization rejects pending/incomplete labels, omitted output spans, changed original artifacts/assets, unsupported corrected commands, and invalid exports. It refuses to overwrite an existing output directory. It produces:

- `review.json`, `source.json`, and copied source assets.
- `scores.json`, always computed from the selected original candidate and its annotations.
- `reviewed-target.json` and `reviewed-notes.md` for accept/edit decisions; rejected drafts remain scoreable without a reviewed export.
- `manifest.json`, with revision ID, time, and file hashes. Hashes detect drift; they are not a signed third-party attestation.

Keep original attempt files accessible until finalization. Container-created drafts must be finalized with the same original mount paths. Finalized bundles retain source assets and can be evaluated after the original attempt is archived. Changing a finalized bundle invalidates its hash checks; create a new revision instead.

## Evaluate selected reviews

```powershell
.venv/Scripts/reel-to-md evaluate outputs/reviews/clip-01-final-v1 outputs/reviews/clip-02-final-v1 --output outputs/evaluations/development-v1
```

This writes `clip-scores.csv`, `summary.json`, and `report.md`. CSV cells are guarded against spreadsheet formulas. Reports include raw numerators/denominators, micro totals, macro averages over eligible clips, source-group counts, decisions, and observed target schema/semantic validity counts. Zero denominators are N/A, never perfect scores. Empty answers get zero recall when source facts exist. Rejected drafts are included; they must not be filtered out to improve reported quality.

Implemented metrics follow [the evaluation protocol](05-evaluation.md): synthesis recall, end-to-end recall, unsupported claim rate, source error rate, citation support precision, reference validity, exact technical accuracy, conflict recall, uncertainty recall, and unnecessary uncertainty. Synthesis recovery requires a source-correct, fully input-supported matched unit; end-to-end recovery requires source correctness. References count original asserted occurrences, not global unique IDs. Citation support counts links for each factual atomic unit.

Aggregation rejects duplicate clip/condition/variant, original-attempt, and review identities. Known source-video hashes must have consistent clip/group/partition/synthetic labels. Synthetic, challenge, development, condition, and first-pass/reviewed variants remain in separate cohorts. No natural clips are inferred from synthetic examples. The detailed CSV uses explicit numerator/denominator/value columns; it is not a filled version of the older blank study scorecard.

To score a corrected output, create and label a new review explicitly:

```powershell
.venv/Scripts/reel-to-md review-init outputs/jobs/JOB/attempts/ATTEMPT --video data/private/clip-01.mp4 --target outputs/reviews/clip-01-final-v1/reviewed-target.json --output outputs/reviews/clip-01-reviewed
```

It is marked `reviewed`, so its scores cannot be pooled with `first_pass`. Editing the correction never changes original scores.

## Scope and next gates

This is a human-labeled **development/challenge** workflow. It does not implement blinded comparisons, frozen audit/test execution, group bootstrap intervals, automatic semantic judging, or baseline/ablation generation. It cannot measure request-level first-pass validity or export success from a selection of finalized reviews. Unsubmitted, pending, and pre-evidence failures are not silently counted as successes; their coverage is unknown in this report. Retain all pipeline run records for a later complete job/request denominator.

If no structured target was produced, a rejected review can record its source facts and zero recovered recall. Its atomic output claim metrics are N/A; the displayed raw model response is not automatically converted into structured claims. Do not treat those N/A values as evidence of safe or supported raw text. Malformed reference occurrences in a parsed target remain countable, including empty/nonstring IDs, and cannot be labeled supporting.

Synthetic checks test the mechanics. Two real clips and human source review are still needed to close the first milestone. Docker remains optional; rebuild the image to include new commands. No model rerun is required merely to review an existing attempt.
