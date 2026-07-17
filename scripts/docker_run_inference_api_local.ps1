param(
    [string]$ImageName = "finance-llm-platform-inference-local:v1",
    [string]$AdapterLocalDir = "outputs\qLoRA-finance-runB-r16-lr2e4",
    [string]$ApiKey = "dev-finance-api-key",
    [int]$Port = 8000,
    [switch]$MockMode
)

$ErrorActionPreference = "Stop"

Write-Host "Building local inference Docker image..."

docker build `
    -f docker/inference/Dockerfile `
    -t $ImageName `
    .

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed."
}

$envArgs = @(
    "-e", "BASE_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct",
    "-e", "FINANCE_API_KEY=$ApiKey",
    "-e", "MODEL_ID=qwen2.5-3b-finance-runB-r16-lr2e4",
    "-e", "LOAD_IN_4BIT=true"
)

if ($MockMode) {
    $envArgs += @("-e", "USE_MOCK_MODEL=true")
}

$volumeArgs = @()

if (-not $MockMode) {
    if (-not (Test-Path $AdapterLocalDir)) {
        throw "Adapter local directory not found: $AdapterLocalDir"
    }

    $AdapterFullPath = (Resolve-Path $AdapterLocalDir).Path
    $volumeArgs += @("-v", "${AdapterFullPath}:/app/adapter:ro")
    $envArgs += @("-e", "ADAPTER_LOCAL_DIR=/app/adapter")
}

Write-Host "Starting container on port $Port..."

docker run --rm `
    -p "${Port}:8000" `
    @envArgs `
    @volumeArgs `
    $ImageName