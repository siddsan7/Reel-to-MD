# Local video workspace

The browser UI uploads a local video, shows real pipeline stages, presents draft notes beside the video and evidence, and downloads validated Markdown. It runs on literal `127.0.0.1`. It uses the existing local models and validators. No paid APIs, remote assets, model rentals, account, or public service are involved.

## Start on Windows

After the local model setup:

```powershell
./scripts/start-ui.ps1
```

Open **http://127.0.0.1:8791**. Keep the terminal running. Press Ctrl+C in that terminal to stop the app. Closing the browser does not stop processing.

The launcher reads `data/private/local-ui-config.json`. New `setup-local.ps1` runs generate this file through `configure-local.py`. For an existing installation, generate it with the project environment:

```powershell
.venv/Scripts/python.exe scripts/configure-local.py
```

That setup command reads installed model digests and writes the standard configuration plus a separate UI profile: 16,384 context tokens, 2,048 output tokens, eight Ollama threads, and a 1,200-second per-call deadline. It does not download models or call inference. The standard configuration keeps its original settings. CPU inference can take several minutes per stage; the longer deadline does not make it faster.

To choose another configuration, port, or private store:

```powershell
./scripts/start-ui.ps1 -Config data/private/my-config.json -Port 8791 -Store outputs/local-ui
```

The underlying CLI is also available:

```powershell
.venv/Scripts/python.exe -m reel_to_md.cli serve --config data/private/local-ui-config.json --store outputs/local-ui --port 8791
```

Without `--config`, `serve` starts in visibly labeled extractive mode. It does not silently enable ASR or synthesis models. Ports are bound only to `127.0.0.1`.

## Use the workspace

1. Select or drop a supported video, then choose **Create notes**. Limits: 100 MiB, 120 seconds, and 3840×2160 pixels. English short tutorials are the current scope.
2. Follow the queue, current stage, completed stages, cache reuse, and elapsed time. The upload has a byte percentage; model stages have no invented percentage or ETA.
3. Read the draft and its unknowns. Select an evidence ID to open the corresponding extraction. Timestamp buttons seek the original video. Selected source frames remain available.
4. Choose **Export Markdown** after validation passes. The download is canonical UTF-8 Markdown with LF line endings. Missing channels and uncertain extraction remain explicit; an invalid draft cannot be exported.

This page supports reading and checking notes. It does not label the draft factually correct or finalize research annotations. The [detailed human review workflow](11-review-evaluation.md) remains available for formal labels, corrections, finalization, and evaluation.

## Automatic draft mode

With a configured text model, automatic drafts now select up to eight exact source excerpts with bound citations. The UI labels this mode **Source excerpts**. Qwen chooses useful text; it cannot rewrite it, complete a command, shift a citation, or invent a procedure. Short extraction entries are quoted whole; longer entries can supply whole lines up to 400 characters. Other details remain in the full evidence. The pipeline and download route reject any broken binding.

This preserves ASR/OCR and visual-report errors instead of silently repairing them. Drafts remain partial and unreviewed. Reading the original video is still required for source fidelity, relevance and completeness. Formal human review can produce richer corrected notes through the existing workflow. Earlier freeform attempts remain in job history; they are not silently changed. See [the decision](decisions/0003-bound-excerpt-drafts.md) and [checks](reports/excerpt-grounding-fix.md).

## Cancellation and recovery

**Cancel processing** stops the owned UI worker and its extraction subprocesses. It keeps the uploaded file, completed caches, diagnostics, and prior attempts. Queued work can be cancelled before it starts. A shared Ollama request may still finish after its client disconnects; the app does not terminate the shared model server.

Choose **Recover job** on cancelled, interrupted, or recoverable failed jobs. Recovery uses the job's saved configuration and checks input/version/cache integrity. It creates a new pipeline attempt. Valid completed stages are reused only when their normal content/config/version identity matches. A code or model version change can require fresh processing.

An ambiguous model dispatch is never repeated automatically. Recovery pauses with an explanation unless you explicitly acknowledge that earlier local processing has stopped and permit a new local request. Check the local model server before making that choice. Relevant pending markers and failed response diagnostics are archived, not discarded. A semantically rejected draft is not silently repaired or rerolled; use formal review or a new configuration and a fresh upload.

Only one worker processes this store at a time. OS leases prevent duplicate managers and workers. On Windows, a named kill-on-close Job Object contains worker descendants; admission also checks whether contained processes remain. A server crash can leave the existing worker running, and a replacement server observes it instead of dispatching another. A dead worker becomes interrupted. Normal server shutdown stops active work and leaves queued work saved.

Windows cancellation, worker crashes, server replacement, and recovery are tested. Non-Windows operation has not been verified; interrupted/cancelled recovery requires an explicit process-check acknowledgment there because it lacks the Windows containment guarantee. Docker UI execution has not been tested.

## Saved data

`outputs/local-ui/` is ignored by Git:

- `jobs/<id>/`: uploaded video, configuration snapshot, durable status, attempt list, and private worker log.
- `pipeline/<identity>/`: normal pipeline caches, frame assets, and immutable attempt directories.
- `pipeline/<identity>/recovery/`: preserved ambiguous-dispatch artifacts and stale owned lock records.

The HTTP app serves only known job routes and allowed assets. Host, Origin, session-token, upload-size, source-video/frame hashes, and Markdown validation checks protect the local workflow. Uploaded names and model text render as text rather than executable HTML. All UI assets are packaged with the Python wheel; no JavaScript build or extra runtime dependency is required.
