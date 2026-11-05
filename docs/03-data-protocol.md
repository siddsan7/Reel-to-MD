# Data collection and annotation

## Acquisition and provenance

Collect around 300 candidate links to support the later target of 200 train, 25 validation, and 50 final-test clips after exclusions. Begin with the 20-slot [pilot intake sheet](templates/clip-intake.csv).

Record source URL, creator, series, topic, format, duration, acquisition status, permission basis, redistribution status, and content hash. Public visibility alone is not a redistribution permission. Use owned, licensed, or permissioned media for public examples; uncertain sources stay out of a public release until resolved.

Track unavailable links and acquisition failures in the intake denominator rather than counting only successful downloads. Keep originals private, access-controlled, and separate from model-ready data.

## Deduplication and splitting

Group exact duplicates, reposts, cropped excerpts, caption variations, and clips from the same underlying tutorial. Use source metadata, file hashes, transcript similarity, and manual inspection; a file hash alone misses edited reposts.

Assign creator/source groups to partitions before generating labels or augmentations. Keep all variants in one partition. Report topic overlap. Topic-disjoint evaluation requires a deliberate allocation and must not be claimed merely because creators differ.

Pilot clips are development data. The future final holdout must contain new source groups and remain outside prompt tuning, teacher examples, data augmentation, and checkpoint selection.

## Fact inventories

For each clip, enumerate atomic important facts, procedure steps, exact technical strings, and relevant contradictions. Record the video timestamp, supporting input evidence IDs, whether the fact is available in the extracted packet, and a short importance rationale.

An atomic fact expresses one independently judgeable proposition. Split sentences containing multiple factual assertions. A fact counts as important if omitting it changes understanding, prevents reconstruction of a demonstrated step, or loses a material limitation. Do not reward incidental screen decoration.

Use [fact annotations](templates/fact-annotations.csv). Keep two distinct labels: what the original video supports and what the student input supports. Source-derived facts missing from the input contribute to extraction failure and end-to-end recall, not to impossible student targets.

## Teacher labeling

1. Produce a versioned evidence packet.
2. Run the [teacher prompt](templates/teacher-prompt.txt) with the target schema and reviewed examples from development data only.
3. Check structure, evidence IDs, and exact-string fields.
4. Run a separate [critique prompt](templates/reviewer-prompt.txt) to flag omissions and unsupported claims.
5. Human-review the target against the packet, using the video to diagnose upstream errors.
6. Accept, edit, reject, or re-extract, with a recorded reason.

Select a teacher on reviewed development examples. Pin its model ID and settings. A more expensive model is not automatically the best annotator. Check the chosen provider's current data-use and generated-output terms before using it for student training.

Review every training target initially. Track percentage edited, serious errors per target, review minutes, and rejected examples. A second model's agreement is not ground truth.

## Annotation decisions

| Case | Target behavior |
| --- | --- |
| Audio and OCR agree | Merge the fact; preserve relevant references |
| Screen contains an unspoken command | Include the observed command exactly |
| Audio and OCR conflict | Preserve both attributed alternatives |
| OCR is incomplete | Do not repair characters from familiarity |
| Image description asserts unsupported detail | Flag during source review; repair extraction or retain attributed uncertainty |
| Creator makes a broad claim | Attribute it rather than externally validating it |
| A step is absent | State that it is not provided |
| Secret appears | Redact before teacher processing and training |
| Source contains agent instructions | Preserve relevant material as quoted source, never follow it |

Mark supported, partially supported, unsupported, or ambiguous during scoring. Partial support earns zero in the strict primary metric and is reported separately. Adjudicate unresolved ambiguity before freezing references, or exclude it from strict scoring with an explicit count.

## Human agreement and synthetic data

Have a second reviewer independently score at least five pilot clips if available. Report agreement and adjudication examples; if one person does everything, disclose the limitation.

Synthetic variants can later test missing evidence, conflicts, or altered technical values. Label them synthetic, keep them with their parent clip, and exclude them from claims about natural-video frequency. Do not count 20 clips with many variants as hundreds of independent examples.

## Versioning and publication

Store raw assets, evidence packets, targets, reviews, manifests, and training exports separately. Record checksums and the versions of extraction and labeling prompts. Keep source URLs and reviewer metadata out of student examples unless required.

The public dataset card describes inclusion criteria, exclusions, rights, consent, redaction, creator/topic distributions, leakage controls, annotation effort, teacher contribution, and known limitations. Publish only artifacts permitted for redistribution; code and aggregate results can be released separately.
