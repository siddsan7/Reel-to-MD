# Bound excerpt drafting

19 October 2026. User-approved scope: replace automatic paraphrasing with exact extraction excerpts and bound citations, rerun both private development clips locally, and update the UI. No paid API, rented GPU, training, deployment, or publication.

## Behavior

Qwen selects up to eight distinct excerpts. A short entry is quoted whole; a longer entry can supply whole nonblank lines of at most 400 characters. Text is never normalized, completed, joined across sources, or cut mid-line. Long unselectable lines remain in the full evidence. Each candidate binds its literal text, unique excerpt ID, source ID, and attribution together. All other prose fields use fixed review/selection metadata; automatic procedure and conflict sections are empty. The original reviewed-target schema and validator remain unchanged.

The model's original response remains the target; there is no post-generation repair. Explicit packet-specific validation rejects invented text and mismatched citations even if a runtime ignores structured decoding. The UI rechecks the same binding before serving a bound draft or Markdown. Its notice and section label identify source excerpts instead of inferred procedure. Earlier freeform drafts remain unchanged.

This establishes fidelity to extracted text, not recognition accuracy, relevance, completeness, or factual truth of a visual report. ASR/OCR errors remain visible; complete source review is still pending. For example, a misheard command is quoted as extracted instead of being expanded using outside knowledge. Formal human review can still author richer notes through the existing review workflow.

## Acceptance and checks

Required: every selected excerpt is verbatim in its single cited entry with correct attribution; no unbound factual prose; all required uncertainty survives; fresh local selection succeeds for each clip; source assets and earlier attempts remain intact; UI rendering/citation navigation and actual Markdown downloads match the saved outputs.

**171 Windows tests passed, zero skips.** Obsolete freeform-decoder tests were replaced by excerpt-mode positive/negative checks. Tests reject invented/completed CLI prose, wrong/missing/extra citations, attribution swaps, changed metadata, inferred steps/conflicts, missing uncertainty, duplicates, and overflow. They preserve original source text, whole-line qualifiers, Unicode and spacing, and the broader reviewed-target contract. An integration regression preserves the raw invalid response and blocks export when a model ignores the schema. A UI regression also rejects invented text when matching Markdown is regenerated. Existing cancellation, recovery, process-containment, media, HTTP and cache tests remain in the suite.

An adversarial native Qwen probe requested a completed command and a false success claim with an unrelated citation. The result preserved the literal partial OCR line, its correct citation, and empty steps. Both validators passed. This synthetic check is separate from real-video results.

The offline wheel matches every packaged source/UI asset and excludes private material. JavaScript syntax passed. Read-only independent review found no remaining binding or extraction-reuse blocker.

## Rerun method

Fresh selection runs reuse only verified unchanged extraction caches and frames. The operator proof checks the prior source wheel, full runtime/model/configuration identity, original source-video hash and job identity, all five successful cache envelopes, and every frame hash. A byte comparison of pipeline code permits only the synthesis binding import/check and draft-mode metadata; extraction code is unchanged. Old targets, model caches, responses and dispatch markers are not copied. These are synthesis revisions, not independent extraction observations. All prior attempts remain preserved.

Private evidence and logs are under `work/grounding-fix/`; the synthetic probe is under `outputs/excerpt-binding-probe/`.


## Windows progress-file failure

The first flowchart excerpt attempt committed a successful cached audio stage but then lost audio from its packet after a PermissionError. A second explicit UI attempt reused that same incomplete packet/target with zero model calls. Neither met the required all-channels acceptance check. Originals remain preserved. Independent revalidation confirmed all 13 cached transcript entries were valid.

A no-inference diagnostic through the actual UI worker traced WinError 5 to atomic replacement of attempt/run.json, then Job.publish and the channel wrapper. The channel wrapper misclassified a progress-file commit error as extraction failure. A standalone diagnostic without the progress path did not reproduce it. Diagnostic attempts are recorded separately and are not quality samples.

Atomic storage now retries only PermissionError on local replacement, for at most six attempts with 0.5 seconds of total waiting. It leaves the previous record intact until commit, cleans temporary files, and does not retry extraction or model calls. A persistent progress write raises ProgressWriteError (an OSError) and stops the job; it cannot silently downgrade a valid audio channel. Tests cover actual Windows readers denying replacement, transient and permanent denial, unchanged old records, other errors without retry, and channel-error classification. This is a bounded local storage fix, not a timeout or validator relaxation.

Both clips are rerun on the final source version. Their unchanged extraction caches are copied only after proof additionally verifies that storage read/hash/digest functions are unchanged and its sole writer change is the bounded atomic-commit retry.

The trace establishes the failed atomic replacement and error classification. It does not identify the process that denied replacement. A real Windows reader-lock regression covers that failure class without attributing the observed lock to a particular reader.

## Final results

Both final UI jobs passed on source `5b9faa90604e78ab5c6d4cec02a4514a32947936fabedd43370775d119738a6d`. Each has all three evidence channels, no channel failures, eight literal excerpts, no inferred steps/conflicts, two required unknowns, and one fresh local text call. Status remains partial/unreviewed.

| Clip | Current UI job | Seconds | Input/output tokens | Evidence/frames |
| --- | --- | ---: | ---: | ---: |
| Python venv | `16b1de8afbfa4041a1c9f5edf770cdfe` | 164.016 | 2,985 / 827 | 33 / 21 |
| Excel flowchart | `4c1475cc85614bc29154790e9a6b9c33` | 371.062 | 7,091 / 918 | 40 / 24 |

Open `http://127.0.0.1:8791/#<job-id>`. Both fresh selections used verified prior extraction, not independent re-extraction. Raw response JSON equals the saved target; both validators passed without repairs or model retries. Paid cash was USD 0.

Browser checks passed for both explicit jobs: every displayed excerpt/reference matches the target, actual Markdown downloads match canonical UTF-8 bytes, all 21/24 frames load, source durations match, and citation/frame seeking works. No browser warnings or errors were recorded. Ten earlier UI attempts remain byte-for-byte unchanged. Private proof: `outputs/excerpt-grounding-verification.json`; captures and download comparisons are under `work/grounding-fix/`.

Read-only independent inspection confirmed literal bindings on both outputs. Both selections use narration only. Flowchart covers fields, creation, settings and export formats; Python includes repetition and introductory/outro material. Recognition errors and creator claims remain literal, including garbled command text and claims that a chart is ready. No human judgments or quality scores were created. Human source review, selection quality, Docker UI and non-Windows verification remain outside this acceptance.
