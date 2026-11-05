# Real-clip synthesis failures and local fix

Date: 19 October 2026. Scope: user-authorized local synthesis repair and reruns of the two approved development clips. No paid API, GPU rental, public release, or training. Original attempts and review bundles remain unchanged.

## Diagnosis

The original Python synthesis timed out after 300.125 seconds. Its full message was 17,619 characters. Vision completed first; no structured target or Markdown was produced.

A separate bounded one-token context probe reproduced the flowchart rejection: HTTP 400, `exceed_context_size_error`, request **10,956 tokens**, available context **8,192 tokens**. The diagnostic is private at `outputs/synthesis-diagnosis.json`. This confirms context overflow rather than a network or credential failure. The original first-pass HTTP response body had not been retained, so the earlier report correctly left its cause unconfirmed.

Both requests duplicated the packet-specific decoding schema inside the prompt and the API structured-output field. The schemas added 6,869 and 7,166 characters respectively, including repeated evidence IDs. Escaped Unicode and JSON whitespace added further input overhead. No evidence may be discarded just to fit the context.

## Changes and acceptance

`synthesis_messages` now sends the complete, unchanged evidence packet as compact UTF-8 JSON. The full packet-specific schema is still sent through structured decoding. The prompt asks for concise, merged facts without repeating the same fact in claims and steps. No target is repaired after generation, and the original target/schema/semantic validators remain unchanged.

HTTP failures now retain a private, redacted error body, status, and truncation flag. Reads are bounded to 16,385 bytes, with at most 16,384 redacted characters retained. The original exception, unknown usage, and ambiguous-dispatch marker remain; errors do not trigger retries.

Reruns use the separate private profile `data/private/local-config-real-v2.json`: eight Ollama threads, 16,384-token context, 2,048-token output cap, 600-second per-call limit. These are existing bounded options. The context increase follows the measured overflow and leaves room for generated notes; the timeout accommodates CPU work. The original default profile remains available. Models, revisions, extraction settings, `truncate:false`, `shift:false`, local-only transport, and human-review requirements are unchanged.

Acceptance: both new attempts must retain all required evidence channels, pass the unchanged validators, export Markdown, create pending reviews with matching original video/frame hashes, and replay from cache with zero new model tokens. Preserve and report any failure rather than weaken checks.

Before the expensive rerun, all **127 tests passed**, including literal Unicode/spacing preservation, bounded redacted HTTP diagnostics, unknown usage, and no repeat dispatch after failure. Independent read-only code review found no blocker. Source/config hashes isolate new jobs from original caches and failed dispatch markers. Clips run sequentially. No application source changes are made during the batch.

## Results

The first revised batch is retained in `outputs/development-processing-summary-v2.json`. Python synthesis returned in 263.641 seconds (2,976 input/1,587 output tokens), but the unchanged validator rejected a command paired with the wrong OCR source. Diagnostic-only in-memory checking also found ten unacknowledged uncertain entries. Its full attempt took 576.063 seconds. No repaired target was saved.

Flowchart passed the former context rejection but synthesis exceeded 600 seconds; full attempt 984.407 seconds. A private local runner snapshot showed 6,986 processed prompt tokens and 1,715 decoded tokens while generation continued near its cap. Total call usage is unknown because the request timed out. The runner used CPU only and 16,384 context; an observed synthesis process used about 4.8 GiB RAM. This is a single observation, not a hardware benchmark.

The next revision narrows command decoding further: a non-null command must be an exact line from one cited normal OCR entry; null-command prose can retain multiple citations. Literal spaces are preserved. It also supplies small packet-derived `REQUIRED_UNKNOWNS` objects in the prompt, including every uncertain evidence ID. This runtime did not fully honor the schema's `prefixItems`, so those obligations must be explicit and still checked by the original validator. The prompt aims for about 150 words of factual prose, excluding commands, IDs, and required unknowns; it requests important details and explicit omissions. This is a soft draft-length instruction, not source truncation or a quality guarantee. The same 600-second limit remains.

All **130 tests passed** before the next generation. New checks cover eligible commands paired with the wrong source, matching source acceptance, uncertain-source rejection, literal spacing, multi-source prose, and explicit missing/truncated/uncertain requirements. Independent review found no blocker.

Only `generation.py` and `prompts/teacher-prompt.txt` differ from the saved, verified v2 wheel for the next batch. A private operator script explicitly reuses the five successful extraction caches and original frames: it verifies the prior wheel/source identity, unchanged extraction code, identical configuration/tool/model versions, input/job identities, successful stage records, envelope digests, safe frame names, and copied hashes. It creates a fresh job and records `extraction-reuse.json`. It never copies targets, model cache, pending markers, or human labels. Normal pipeline validation then runs again. This is scoped experiment reuse, not a shipped general cache migration feature or an independent extraction rerun.

The v3 batch is recorded in `outputs/development-processing-summary-v3.json`. Python passed the unchanged original validator and the generation schema: 195.485 seconds, 3,233 input/894 output tokens, four claims, three steps, and one uncertainty entry. Its bundle has 22 assets and 12 pending review units. Independent artifact verification passed. Its exact-version cache replay passed in 0.063 seconds with zero new tokens or model calls.

Flowchart v3 still timed out after 600.172 seconds. A later runner snapshot showed 7,343 processed prompt tokens and 990 decoded tokens while generation continued. The full v3 batch checker correctly failed on this attempt, after recording the successful Python checks. It was not modified to skip failures. Original results remain in all earlier summaries and bundles.

## CPU deadline reassessment

Two completed, progressing flowchart attempts exceeded the 600-second ceiling. Local tokenizer measurements did not justify a new encoding: shared-line layouts saved little or increased tokens; columnar JSON saved only about 7.5% before additional format instructions. Those prototypes were not shipped. No evidence is removed, truncated, normalized, or replaced.

The explicit CPU deadline ceiling is now 1,200 seconds, with the default still 300 seconds. The new private profile `data/private/local-config-real-v4.json` changes only the client deadline from the prior 600-second profile. Context stays 16,384, output stays 2,048, threads stay eight, and all validators stay unchanged. This permits slow local work; it is not a claim of improved throughput. Defaults are unchanged for other users. Boundary tests accept 1,200, reject 1,201/zero, verify the default, and verify the deadline reaches the request. All **131 tests passed**; independent review found no blocker.

Only flowchart needs another inference attempt. Python's validated v3 review remains unchanged. Extraction reuse is checked again: old identity uses the old configuration, new identity the new configuration; all fields except the longer client deadline match. The private script proves that `pipeline.py` and `providers.py` differ from the saved v2 wheel only in one exact timeout-bound comparison each. Media/extraction/provider payload code is unchanged; all reused extraction requests succeeded under the earlier deadline. Both versions/configurations and cache/frame hashes are retained in the new provenance record. No target, model output, pending marker, or reviewer label is imported.

The v4 flowchart response completed in 671.907 seconds, with 7,341 input and 1,819 output tokens. The original validator rejected missing uncertainty coverage; no Markdown was exported. This resolved the transport timeout but did not meet draft acceptance. Private summary: `outputs/development-processing-summary-v4.json`. The strict final checker requires both explicit current drafts, checks every earlier attempt, and retains failed-history counts. No paid API or rented GPU was used. Docker inference is not rerun for this native CPU repair.


## Decoder compatibility

The installed local decoder did not enforce `prefixItems` when the same array also had `items`. Its behavior matches the limitation documented in the upstream [grammar documentation](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/grammars/README.md) and the [schema conversion tests](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tests/test-json-schema-to-grammar.cpp). An explicit prompt requirement alone did not ensure complete coverage.

The generation schema now uses fixed tuple alternatives without an `items` sibling. Each alternative begins with the exact required uncertainty objects, including every uncertain evidence ID. Shared flat definitions keep the schema compact. It permits zero to 16 additional uncertainty entries; this is a generation bound, while the original target contract remains unchanged. Related additional gaps can share an entry. No evidence is dropped and no generated target is supplemented.

Two live, local decoder probes passed even when the synthetic prompt requested an empty uncertainty list: a tiny tuple probe and a second probe with the actual full flowchart uncertainty list and shared references. The latter returned 238 tokens. These are decoder checks, not factual-quality evaluations. All 131 project tests passed with zero skips in the locked environment. An initial launch with the system Python stopped at the runtime-version guard before inference; it was relaunched with the project's environment. Independent read-only review found no blocker.

The next targeted flowchart attempt uses the same explicit 1,200-second CPU profile. Python's valid v3 draft remains unchanged. The strict acceptance checker audits all earlier attempts, selects the current versions explicitly, and refuses to hide failed rows.


## Consecutive step decoding

Flowchart v5 completed in 589.297 seconds. Its response passed the generation schema and contained the full mandatory uncertainty list. The unchanged semantic validator rejected a repeated step number: after steps 1 through 8, the model emitted 6 again. No Markdown was exported, and its response and pending review remain preserved.

The generation schema now also uses position-specific fixed tuples for steps. It permits an empty procedure or 1–32 consecutively numbered steps. Flat shared definitions retain the existing exact-command/source binding at every position. The prompt documents the bound and asks for grouping or explicit material omissions if needed. This is a generation bound, not evidence truncation; the original target contract and semantic checks remain unchanged.

A bounded live negative-prompt probe requested two steps both numbered 1. The installed local runtime emitted 1 and 2, and schema validation passed (44 input/121 output tokens). All 135 project tests passed with zero skips. Regression checks cover duplicate numbers, skipped numbers, a first number other than 1, 33-step rejection, and acceptance of empty, one-step, 13-step, and 32-step procedures. Independent read-only review found no blocker. A separate flowchart v6 attempt follows; Python v3 remains the selected valid draft.


## Final accepted drafts and checks

Flowchart v6 passed the unchanged original schema and semantic validator, as well as the current generation schema, in **524.609 seconds** (7,382 input/1,707 output tokens). It has seven claims, 13 consecutively numbered steps, one complete uncertainty entry, and one omission. Its review contains 23 pending units and 25 assets. Python's selected v3 draft remains valid at 195.485 seconds, with 12 pending units and 22 assets. Both are partial drafts awaiting human source review.

Current private pages:

- Python: `outputs/reviews/python-venv-01/b78a1782942448b68e26be613677c62b/review.html`
- Flowchart: `outputs/reviews/flowchart-excel-01/300ee9b085d74c5081d4268c77082b4f/review.html`

The strict final checker passed for both selected drafts and audited all **nine** inference attempts, including **seven** preserved failures. Raw responses equal the targets; Markdown equals the deterministic rendering; source snapshots, original video hashes, copied frame/assets, page content, CSP, extraction provenance, and pending human annotations passed. It rejects premature human finalization. Flowchart's exact-version replay passed in **0.031 seconds**, all stages cached with zero new tokens/model calls. Python's retained exact-version replay passed in **0.063 seconds**, also with zero new tokens/model calls. No earlier failure is relabeled as success. Private verification: `outputs/development-final-verification.json`.

All **135 tests passed**, zero skips, in the locked environment. The offline v6 wheel built, matches every packaged source file byte for byte, and excludes private inputs/configuration/results. Diff whitespace checks passed. The review workflow's browser visuals, video playback, and annotation download remain manual checks; no browser restriction was bypassed. Docker was not rerun for this native repair. CPU latency remains substantial; increasing a deadline does not improve throughput.

All work and inference stayed local on CPU. Paid cash is zero; no paid API or rented GPU was used. Usage for timed-out calls remains unknown. Human factual labels, source-fact inventory, corrections, reviewer identity, approval, and quality scores remain pending. The larger implementation milestone still requires that human review and later Android share/retrieval work.
