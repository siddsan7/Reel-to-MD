# Real clips in the local UI

Follow-up: the user selected exact excerpts with bound citations. Latest automatic drafts and final checks are in [bound excerpt drafting](excerpt-grounding-fix.md). This report preserves the earlier freeform results and their limitations.

19 October 2026. Scope: upload both approved development videos through the browser, observe local progress and queueing, inspect notes and source evidence, and check Markdown exports. No paid APIs, rented GPUs, deployment, or training.

## Initial full runs

Both uploads completed all five extraction stages and synthesis with the original validators passing. Python: 556.891 seconds, 21 frames, 33 evidence entries. Flowchart: 951.110 seconds, 24 frames, 40 evidence entries. All three evidence channels were available. Each run made four fresh local model calls. Paid cash: USD 0.

Browser checks observed live frame selection, vision and synthesis progress, queueing, source playback, evidence navigation, and timestamp seeking. The Python browser download equals canonical UTF-8 Markdown byte for byte. Private backend proof is `outputs/local-ui-real-verification-initial.json`; progress and browser artifacts are under `work/ui-real/`.

Schema validity did not establish factual correctness. Inspection found a filename, heading, and mid-animation activation fragment promoted into commands in Python. The draft also missed the central narrated purpose. Flowchart procedure citations were shifted in early steps, and vendor/outro content became procedure. These original targets and responses remain preserved.

## Versioned draft changes

The drafting prompt now centers the narrated task, requires the actual supporting evidence IDs, excludes promotional/outro content from procedure, distinguishes demonstrations from recommended actions, and leaves incomplete commands as prose or uncertainty. Decoding requires normal OCR and positive literal matching normal narration before emitting any exact command. Other OCR strings remain available as attributed evidence with command null. Source text is unchanged; no generated target is repaired, and the original validator remains unchanged.

The two new uploads use a separately recorded, explicit reuse of unchanged extraction. Before copying caches, the operator check verifies the original wheel/source hash, the complete unchanged runtime/tool/model/configuration record, source video hashes, old job identities, successful extraction envelopes, and every source frame hash. Only extraction cache envelopes and declared frames are copied to fresh pipeline identities. Old targets, model response caches, and pending dispatch markers are excluded. This is a synthesis revision using verified prior extraction, not an independent extraction rerun.

A prompt-only revision failed after 497.562 seconds at the unchanged 2,048-token limit: it repeated a partial activation command beyond 24 steps. Its incomplete raw response, usage record, and pending marker remain saved. The second revision job was cancelled through the browser after about three minutes. The worker stopped, the model queue subsequently emptied, and all completed evidence stayed available; the UI offered explicit recovery and no export.

The subsequent decoder limits automatic drafts to six claims and eight consecutive steps, with 400 characters per prose item. This limits output growth; it does not establish completeness or prevent all semantic repetition. The original reviewed-output contract is unchanged. An adversarial synthetic native probe requested nine steps; the local runtime returned eight valid consecutive steps. The full Windows suite passed **167 tests, zero skips**. Offline wheel source/assets/private-exclusion and diff checks passed. Excluded commands remain unchanged in the packet. Literal matching also rejects executable-name prefixes such as `deactivate.exe` when checking `deactivate`.

## Final workflow checks

Both bounded drafts completed with the original schema and semantic validators passing. Python: 299.312 seconds, 3,608 input / 1,297 output tokens. Flowchart: 523.031 seconds, 7,719 input / 1,427 output tokens. Each made one fresh text-model call and reused the five explicitly verified extraction stages. Paid cash remained USD 0. These synthesis revisions do not count as independent extraction observations.

- Python UI: `http://127.0.0.1:8791/#97477b8eda3c4c9f91f18d86c5a43587`.
- Flowchart UI: `http://127.0.0.1:8791/#1d50262048e449bebf8a4a1ab495377b`.

The browser rendered every note item, command field, and reference exactly as stored. All 21/24 frame images loaded; source durations matched the acquired clips; citation navigation highlighted the correct evidence and timestamp controls sought the video. Both actual browser downloads equal canonical UTF-8 Markdown byte for byte. Switching jobs cleared stale evidence and retained the correct source. Browser warnings/errors: none observed.

Strict backend verification checked complete channels, original/generated validation, raw-target identity, configuration and runtime versions, source/frame/API hashes, zero new extraction calls, fresh synthesis, no pending dispatch after success, and observed progress. A separate history audit checked all six UI attempts against preserved source-wheel snapshots and verified that failed/cancelled exports return the defined rejection. Private evidence: `outputs/local-ui-real-verification.json`, `work/ui-real/`, and the initial full-run record. The offline final wheel contains matching source/UI assets and excludes private files. All 167 tests pass with zero skips; diff checks pass.

## Grounding limitation

The bounded Python draft passes structural validation and exports, but an independent agent inspection against its evidence packet **failed grounding and relevance checks**. It expands garbled or partial CLI text into complete commands inside prose even though command fields are null, retains decorative/blank-frame content, and uses observations as procedural steps. This is not proof that those commands are intrinsically false; the cited extraction does not establish them. No reviewed labels or quality scores were invented, and no output was repaired.

The flowchart draft improved early citation ordering and excluded the promotional procedure, but still has details supported by other uncited packet entries and an unsupported success claim. Its grounding acceptance also remains pending.

The current workspace is suitable for inspecting and exporting unreviewed drafts. It is not accepted for unattended trusted notes. Decoder bounds and command-field guards are mechanical controls, not semantic entailment checks. Human source review and improvements to synthesis selection/grounding remain separate work.

## Limits

Human source-fact inventories, formal judgments, and quality scores remain pending. These two development videos do not establish general model accuracy. The UI supports inspection and export; formal annotations and finalization remain in the existing review workflow. Windows cancellation and recovery have automated and synthetic browser coverage. Docker UI and non-Windows behavior remain unverified.
