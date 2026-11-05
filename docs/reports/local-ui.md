# Local UI implementation and verification

19 October 2026. Goal: upload → real progress → evidence-linked draft review → Markdown export, with cancellation and recovery. Constraints: local files and loopback inference only, no paid API or GPU rental, original validators unchanged, preserve previous attempts and ambiguous dispatches.

## Implementation

- Python standard-library loopback HTTP server and packaged HTML/CSS/JavaScript. Responsive notebook workspace, persistent job list, video playback, selected frames, citation navigation, elapsed stage progress, and canonical Markdown download.
- One durable queue worker per store; separate manager and execution OS leases. Each upload has an immutable configuration snapshot and content hash. The existing pipeline publishes stage snapshots before and after work and still owns cache integrity and final validation.
- Cancellation stops the owned worker tree. Windows [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) retain process containment even on a worker crash. The manager checks named containment and leases, not persisted process IDs, before admission. A replacement server observes a surviving worker.
- Explicit recovery creates another attempt, reuses verified caches, and archives relevant uncertain-dispatch diagnostics only after human acknowledgment. Invalid semantic drafts cannot bypass validation or be exported. A disconnected shared model request may still complete; the shared model server is left running.
- Literal loopback bind, Host/Origin/session-token guards, bounded streaming upload, fixed job/asset routes, no external assets, restrictive CSP, inert model/source text, video/frame hashes, and deterministic export checks. No new dependencies or framework lockfile were needed.
- `scripts/start-ui.ps1`, CLI `serve`, and a separate setup-generated local UI CPU configuration. See [usage](../12-local-ui.md).

## Checks

**154 tests passed with zero skips** on Windows. JavaScript syntax checks and the offline wheel build passed. Every packaged source file matches byte for byte, all UI assets are present, and private media/configuration/results are excluded. New regression tests cover real HTTP upload and rejection boundaries, byte ranges, source/frame/Markdown corruption, live progress persistence, queue cancellation, cache recovery, explicit uncertain-dispatch handling, preserved raw diagnostics, store ownership, and failed-validation guards.

Real subprocess checks cover deliberate cancellation, forced worker death with a child writer, malformed cancellation records, taskkill failure, and killing a coordinator before reconnecting to its surviving worker. Read-only independent review identified the crash-containment and watchdog gaps; both were fixed and verified. A later minor status issue was fixed so one job's cancellation does not follow another worker.

The in-app browser completed a synthetic two-second video upload, real FFmpeg/Tesseract processing, valid extractive draft, source playback (readyState 4), citation navigation, and Markdown download. Download bytes equal canonical UTF-8 rendering exactly; Windows on-disk CRLF is normalized to canonical LF on export. A second synthetic run used a deliberately injected extraction delay to exercise visible cancellation and recovery. It preserved the interrupted attempt and produced another valid draft. No ASR, vision, or synthesis model calls were made in these UI checks. No console errors were reported. The narrow in-app viewport rendered the responsive single-column layout.

Private evidence: `outputs/local-ui-verification.json`, `work/ui-smoke/`, test/build logs, and screenshots. These fixtures are synthetic workflow checks, not real-video quality results. Earlier real-clip drafts and all their failed attempts remain unchanged.

## Limits

At the initial UI release, real model inference had been checked separately. The subsequent [real UI check](local-ui-real-clips.md) uploaded both clips, verified actual exports, and recorded remaining model-grounding limits. Human factual judgments remain pending. This UI reads drafts and evidence; formal annotation/finalization remains in the existing review workflow. No Docker UI run or non-Windows cancellation/recovery check was performed. The Windows containment guarantee is not claimed for other platforms. No Android intake, URL retrieval, training, hosted deployment, or public release was added.


Final startup found an unrelated service already on the initial port. The UI now defaults to **8791**, binds exclusively on Windows, and starts its queue only after binding succeeds. A failed bind leaves saved workers untouched. Regression checks cover both cases. The unrelated service was not stopped or changed. Final local-model UI startup on port 8791 and the configured synthesis model label were verified in the browser. The synthetic test server was stopped; the user workspace remains running.
