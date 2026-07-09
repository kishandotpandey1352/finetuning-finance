param(
    [string]$AdapterDir = "outputs\qLoRA-finance-runB-r16-lr2e4",
    [string]$ExpectedBaseModel = "Qwen/Qwen2.5-3B-Instruct"
)

$ErrorActionPreference = "Stop"

Write-Host "Validating fine-tuned adapter artifact..."
Write-Host "Adapter directory: $AdapterDir"

if (-not (Test-Path $AdapterDir)) {
    throw "Adapter directory not found: $AdapterDir"
}

$RequiredFiles = @(
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer_config.json",
    "tokenizer.json",
    "README.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $AdapterDir $File

    if (-not (Test-Path $Path)) {
        throw "Missing required adapter file: $Path"
    }

    Write-Host "Found: $File"
}

$AdapterConfigPath = Join-Path $AdapterDir "adapter_config.json"
$AdapterConfig = Get-Content $AdapterConfigPath -Raw | ConvertFrom-Json

Write-Host ""
Write-Host "Reading adapter_config.json..."

$BaseModel = $AdapterConfig.base_model_name_or_path
$TaskType = $AdapterConfig.task_type
$LoraR = $AdapterConfig.r
$LoraAlpha = $AdapterConfig.lora_alpha
$TargetModules = $AdapterConfig.target_modules

Write-Host "Base model from adapter: $BaseModel"
Write-Host "Task type: $TaskType"
Write-Host "LoRA rank r: $LoraR"
Write-Host "LoRA alpha: $LoraAlpha"

if ([string]::IsNullOrWhiteSpace($BaseModel)) {
    throw "adapter_config.json does not contain base_model_name_or_path."
}

if ($BaseModel -ne $ExpectedBaseModel) {
    Write-Warning "Expected base model: $ExpectedBaseModel"
    Write-Warning "Actual base model:   $BaseModel"
    Write-Warning "Make sure inference uses the exact base model shown in adapter_config.json."
} else {
    Write-Host "Base model matches expected model."
}

if ($TaskType -ne "CAUSAL_LM") {
    Write-Warning "Expected task_type CAUSAL_LM but found: $TaskType"
}

$AdapterWeightsPath = Join-Path $AdapterDir "adapter_model.safetensors"
$AdapterWeights = Get-Item $AdapterWeightsPath

Write-Host ""
Write-Host "Adapter weight file size:"
Write-Host "$($AdapterWeights.Length) bytes"

if ($AdapterWeights.Length -lt 1000000) {
    Write-Warning "Adapter model file is smaller than expected. Please verify this is a real trained adapter."
}

$CheckpointDirs = Get-ChildItem $AdapterDir -Directory | Where-Object {
    $_.Name -like "checkpoint-*"
}

Write-Host ""
Write-Host "Checkpoint directories found: $($CheckpointDirs.Count)"

foreach ($Checkpoint in $CheckpointDirs) {
    Write-Host "Checkpoint: $($Checkpoint.Name)"
}

Write-Host ""
Write-Host "Adapter artifact validation complete."
Write-Host "This adapter is ready for S3 upload and inference packaging."