param(
    [string]$AdapterLocalDir = "outputs\qLoRA-finance-runB-r16-lr2e4",
    [string]$BaseModelName = "Qwen/Qwen2.5-3B-Instruct"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AdapterLocalDir)) {
    throw "Adapter local directory not found: $AdapterLocalDir"
}

Write-Host "Testing inference loader..."
Write-Host "Base model: $BaseModelName"
Write-Host "Adapter:    $AdapterLocalDir"

$env:BASE_MODEL_NAME = $BaseModelName
$env:ADAPTER_LOCAL_DIR = $AdapterLocalDir
$env:LOAD_IN_4BIT = "true"
$env:MAX_NEW_TOKENS = "200"
$env:TEMPERATURE = "0.2"

python -m src.inference.test_model_loader

if ($LASTEXITCODE -ne 0) {
    throw "Inference loader test failed."
}

Write-Host "Inference loader test completed."