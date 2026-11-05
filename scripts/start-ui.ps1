param(
    [string]$Config = "data/private/local-ui-config.json",
    [int]$Port = 8791,
    [string]$Store = "outputs/local-ui"
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Python environment missing. Run scripts/setup-local.ps1 first.'
}
if (-not (Test-Path -LiteralPath $Config)) {
    throw 'Local UI configuration missing. Run scripts/configure-local.py with the project Python, or pass -Config with an existing local configuration.'
}
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& .venv/Scripts/python.exe -m reel_to_md.cli serve --config $Config --store $Store --port $Port
if ($LASTEXITCODE -ne 0) { throw 'The local UI stopped with an error. Check its configuration and port.' }
