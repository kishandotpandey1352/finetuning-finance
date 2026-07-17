param(
    [string]$AdapterLocalDir = "outputs\qLoRA-finance-runB-r16-lr2e4",
    [string]$BaseModelName = "Qwen/Qwen2.5-3B-Instruct",
    [string]$ApiKey = "dev-finance-api-key",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AdapterLocalDir)) {
    throw "Adapter local directory not found: $AdapterLocalDir"
}

Write-Host "Starting local Finance LLM API..."
Write-Host "Base model: $BaseModelName"
Write-Host "Adapter:    $AdapterLocalDir"
Write-Host "Port:       $Port"

$env:BASE_MODEL_NAME = $BaseModelName
$env:ADAPTER_LOCAL_DIR = $AdapterLocalDir
$env:LOAD_IN_4BIT = "true"
$env:FINANCE_API_KEY = $ApiKey
$env:MODEL_ID = "qwen2.5-3b-finance-runB-r16-lr2e4"

uvicorn src.api.main:app --host 0.0.0.0 --port $Port