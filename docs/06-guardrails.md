# Guardrails and operations

## Trust boundaries

Media, captions, OCR, transcripts, and visual descriptions are untrusted source data. Teacher and synthesis models have no tools or authorization to execute source instructions. Keep system instructions separate from evidence.

Prompt wording is one control; isolation, validation, and permissions enforce the boundary. See [OWASP prompt injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

## Controls and failure responses

| Risk | Control | Required test or response |
| --- | --- | --- |
| Unsupported facts | Evidence-linked targets and semantic review | Flag or omit; score against input |
| Fabricated commands | Exact-string validation and attributed uncertainty | Block confident invented command |
| Source injection | Tool-free model, delimited evidence, quoted export | Injection fixture must not change task |
| Renderer injection | Escape source text, disable raw HTML and automatic remote loads | Script/HTML/link fixtures |
| Private network fetching | Validate URL schemes, resolve/redirect targets, block private/local destinations, bound redirects | SSRF tests before server URL intake |
| Malformed media | Size/duration limits, isolated patched decoder, timeouts | Oversize/corrupt media fixtures |
| Credentials or personal data | Redact before external calls; human check for dataset inclusion | Synthetic secret fixtures and deletion test |
| Evidence corruption | Unique IDs, valid timestamps, hashes, versioning | Reject invalid packet |
| Missing channel | Explicit channel state and partial result | Missing audio/OCR fixtures |
| Unbounded retries | Maximum two retries for transient transport failures; one recorded schema repair | Stop and report failure |
| Duplicate requests | Idempotent job ID and cache | Same request must not duplicate work |
| Spending overrun | Reserve estimated maximum job cost before dispatch | Reject jobs exceeding remaining cap |

Suggested initial upload limit is 100 MB and 120 seconds for pilot clips. Profile timeouts rather than promising a latency target before measurement. Disable public URL fetching until its protections are implemented; local upload can support the pilot.

## Privacy and retention

Proposed policy: raw media stays in a private project directory; no raw media or full text in routine logs. Redact before sending data to external providers. Keep a list of providers and their retention/data-use settings.

For future service use, propose raw-media deletion seven days after successful processing unless the user explicitly retains it for reviewed research. Remove derived assets and cached outputs on deletion requests according to a documented dependency map. Provider retention and backups require separate disclosure; do not promise deletion beyond control.

Research data requires a recorded permission basis and retention choice. Credential-like values are replaced consistently with placeholders. Automatic detectors miss secrets; manual review remains required before training or publication.

## Serving and monitoring

Record job ID, versions, channel availability, durations, token usage, billed costs, validation outcomes, retries, and non-sensitive error categories. Track export success over accepted jobs, not only successful model calls.

Authenticate users and enforce ownership checks before any multi-user deployment. Isolate assets by user. Keep API keys in environment/secret storage and out of mobile bundles, exports, datasets, and logs.

Maintain a last-known-good model and extraction configuration. Roll back on severe fabricated commands, leakage, or sustained quality regression. User corrections enter a pending review queue, never automatic retraining.

## Export and downstream agents

Exports identify source content as untrusted and source claims as unverified externally. Commands remain inert code blocks. This cannot guarantee another agent will obey the boundary; document that downstream agents need their own controls.

Preserve uncertainty in the rendered Markdown. Do not repair invalid content by silently deleting the evidence of failure. Record original and repaired outputs privately for debugging, subject to redaction/retention rules.

## Release checklist

- [ ] User or assigned reviewer has reviewed the release.
- [ ] Known severe challenge failures are resolved.
- [ ] Regression suite covers changed stages.
- [ ] Costs and retention settings are recorded.
- [ ] Invalid inputs and partial outputs behave visibly.
- [ ] Rollback and deletion have been exercised.
- [ ] Model card, dataset card, limitations, and reproduction instructions match the released versions.

These controls are implementation requirements; this documentation package does not establish that they are implemented.
