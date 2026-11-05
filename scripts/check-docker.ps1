param(
    [switch]$SkipBuild,
    [switch]$SkipModels
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$taskRoot = (Get-Location).Path
$taskDocker = Get-Command docker -ErrorAction SilentlyContinue
if ($taskDocker) {
    $taskDockerExe = $taskDocker.Source
} else {
    $taskDockerExe = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'
}
if (-not (Test-Path -LiteralPath $taskDockerExe)) { throw 'Install/start Docker Desktop first.' }
$env:PATH = "$(Split-Path -Parent $taskDockerExe);$env:PATH"

function Invoke-Docker {
    & $taskDockerExe @args
    if ($LASTEXITCODE -ne 0) { throw "Docker check failed (exit $LASTEXITCODE)." }
}

function Write-CheckJson {
    param($Value, [string]$Path)
    [System.IO.File]::WriteAllText((Join-Path $taskRoot $Path), ($Value | ConvertTo-Json -Depth 20), [System.Text.UTF8Encoding]::new($false))
}

if (-not (Test-Path -LiteralPath 'work/local-smoke/tutorial.mp4')) {
    throw 'Generate the synthetic fixture with scripts/check-local.py first.'
}
New-Item -ItemType Directory -Force outputs/docker-check | Out-Null
$taskSession = 'run-' + [guid]::NewGuid().ToString('N').Substring(0, 10)
New-Item -ItemType Directory -Force "outputs/docker-check/$taskSession" | Out-Null
if (-not $SkipBuild) { Invoke-Docker build -t reel-to-md:local . }
$taskBase = @('run', '--rm', '--read-only', '--tmpfs', '/tmp', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges')
$taskOutput = "type=bind,source=$taskRoot/outputs/docker-check,target=/outputs"
$taskInput = "type=bind,source=$taskRoot/work/local-smoke,target=/input,readonly"
$taskAsr = "type=bind,source=$taskRoot/models/whisper-small.en,target=/models/whisper-small.en,readonly"

Invoke-Docker @taskBase --network none --mount $taskOutput reel-to-md:local check-example /app/example.json --output "/outputs/$taskSession/check"
Invoke-Docker @taskBase --network none --entrypoint /app/.venv/bin/python reel-to-md:local -c 'import os; assert os.getuid() != 0; print("nonroot uid", os.getuid())'
Invoke-Docker @taskBase --network none --entrypoint tesseract reel-to-md:local --list-langs

Write-CheckJson @{ asr_model='/models/whisper-small.en'; input_kind='synthetic_fixture' } "outputs/docker-check/$taskSession/extract-config.json"
Invoke-Docker @taskBase --network none --mount $taskOutput --mount $taskInput --mount $taskAsr --mount "type=bind,source=$taskRoot/outputs/docker-check/$taskSession/extract-config.json,target=/config.json,readonly" reel-to-md:local run /input/tutorial.mp4 --config /config.json --output "/outputs/$taskSession/extract"
& .venv/Scripts/python scripts/verify-docker.py "outputs/docker-check/$taskSession" extract
$taskExtractCode = $LASTEXITCODE
if ($SkipModels) { exit $taskExtractCode }

# Share an isolated loopback namespace, not the host network. No ports are published.
$taskNativeConfig = Get-Content data/private/local-config.json -Raw | ConvertFrom-Json
$taskNativeConfig.asr_model = '/models/whisper-small.en'
$taskCpuCount = [math]::Min(8, [int](& $taskDockerExe info --format '{{.NCPU}}'))
if ($LASTEXITCODE -ne 0 -or $taskCpuCount -lt 1) { throw 'Cannot determine local Docker CPU count.' }
$taskCpuSet = "0-$($taskCpuCount - 1)"
$taskNativeConfig | Add-Member -NotePropertyName ollama_threads -NotePropertyValue $taskCpuCount -Force
$taskNativeConfig | Add-Member -NotePropertyName input_kind -NotePropertyValue 'synthetic_fixture' -Force
Write-CheckJson $taskNativeConfig "outputs/docker-check/$taskSession/model-config.json"
$taskModels = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { Join-Path $env:USERPROFILE '.ollama/models' }
if (-not (Test-Path -LiteralPath $taskModels)) { throw 'Local Ollama weights are missing.' }
Invoke-Docker pull ollama/ollama:0.40.3
$taskServer = 'reel-to-md-smoke-' + [guid]::NewGuid().ToString('N').Substring(0, 10)
$taskStarted = $false
try {
    # Affinity is visible to the inference runtime; a CPU quota alone is not.
    Invoke-Docker run --detach --name $taskServer --network none --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --user 10001:10001 --memory 6g --cpuset-cpus $taskCpuSet --env "OMP_NUM_THREADS=$taskCpuCount" --env HOME=/tmp/ollama --env OLLAMA_MODELS=/models --env OLLAMA_HOST=127.0.0.1:11434 --env OLLAMA_NO_CLOUD=1 --env OLLAMA_VULKAN=0 --mount "type=bind,source=$taskModels,target=/models,readonly" ollama/ollama:0.40.3 serve
    $taskStarted = $true
    # The first read-only inventory request can race server startup; no inference retries.
    $taskReady = $false
    for ($taskIndex=0; $taskIndex -lt 10; $taskIndex++) {
        & $taskDockerExe exec $taskServer ollama list *> "outputs/docker-check/$taskSession/ollama-inventory.log"
        if ($LASTEXITCODE -eq 0) { $taskReady=$true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $taskReady) { throw 'Isolated Ollama did not start; inspect its local logs.' }
    Invoke-Docker inspect --format '{{json .HostConfig.NetworkMode}} {{json .HostConfig.PortBindings}}' $taskServer
    & $taskDockerExe inspect $taskServer > "outputs/docker-check/$taskSession/server-inspect.json"
    Invoke-Docker @taskBase --network "container:$taskServer" --entrypoint /app/.venv/bin/python reel-to-md:local -c 'from reel_to_md.providers import ollama_runtime_version; print("isolated Ollama",ollama_runtime_version("http://127.0.0.1:11434"))'
    foreach ($taskAttempt in @('first','repeat')) {
        Write-Output "Container model attempt: $taskAttempt"
        Invoke-Docker @taskBase --network "container:$taskServer" --mount $taskOutput --mount $taskInput --mount $taskAsr --mount "type=bind,source=$taskRoot/outputs/docker-check/$taskSession/model-config.json,target=/config.json,readonly" reel-to-md:local run /input/tutorial.mp4 --config /config.json --output "/outputs/$taskSession/models"
    }
    & .venv/Scripts/python scripts/verify-docker.py "outputs/docker-check/$taskSession" models
    $taskModelCode = $LASTEXITCODE
} finally {
    if ($taskStarted) {
        & $taskDockerExe logs $taskServer *> "outputs/docker-check/$taskSession/ollama-server.log"
        & $taskDockerExe inspect $taskServer > "outputs/docker-check/$taskSession/server-final-inspect.json"
        & $taskDockerExe stop --time 10 $taskServer | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to stop test server $taskServer; inspect it manually." }
        & $taskDockerExe rm $taskServer | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to remove test server $taskServer; no force removal attempted." }
    }
}
if ($taskExtractCode -ne 0 -or $taskModelCode -ne 0) { exit 1 }
