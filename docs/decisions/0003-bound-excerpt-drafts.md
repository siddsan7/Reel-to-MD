# Bound excerpt drafts

## Decision

Accepted, 19 October 2026. User selected exact excerpts with bound citations. The agent implemented the decoder, persistence fix, and checks; the user has not approved source facts or model quality.

## Problem and alternatives

The local 4B model passed structural validation while completing unsupported CLI strings in prose and citing entries that did not cover its paraphrases. Prompt-only instructions did not prevent these failures. Keeping freeform paraphrases with a second local model review would still provide a fallible semantic check and require more inference. Exact excerpt selection provides a deterministic fidelity check on this hardware.

## Evidence and tradeoffs

The retained development attempts and [verification report](../reports/excerpt-grounding-fix.md) record the failures and new checks. Every automatic factual excerpt is now bound to its exact source entry and attribution. Static review metadata closes other prose channels. Raw model responses remain unchanged, and the original human-reviewed target contract stays available.

The result is less polished and not a reconstructed procedure. Recognition errors, redundant selections, missing visual details, and incomplete coverage can remain. Full evidence and source assets remain accessible. Human source review is still required; mechanical binding does not prove the original video was understood correctly.

A separate Windows progress-file collision was reproduced with model dispatch blocked. Bounded atomic-write retries and a distinct progress error prevent metadata failure from being misclassified as missing audio. They do not retry models or relax acceptance checks.

## Choice and reversal condition

Configured automatic drafting selects at most eight exact excerpts; it emits no inferred steps or conflicts. Pipeline and UI export validate the packet-specific binding and the original contract. All inference stays local. Reconsider freeform automatic synthesis only after reviewed examples and held-out checks demonstrate acceptable grounding; do not silently restore it or post-repair generated outputs.
