$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw 'Setup command failed; inspect its output.' }
}

# Downloads are explicit setup actions; inference uses local files and loopback.
Invoke-Checked { python -m uv sync --locked --extra asr }
Invoke-Checked { ollama pull qwen3-vl:4b-instruct }
Invoke-Checked { ollama pull qwen3:4b-instruct-2507-q4_K_M }
$env:HF_HUB_DISABLE_TELEMETRY = '1'
Invoke-Checked { .venv/Scripts/python scripts/download-whisper.py }
Invoke-Checked { .venv/Scripts/python scripts/configure-local.py }
