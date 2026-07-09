param(
    [string]$Region = "us-east-1",
    [string]$BucketName = "finance-llm-local-artifacts-671607590681-us-east-1",
    [string]$LocalAdapterDir = "outputs\qLoRA-finance-runB-r16-lr2e4",
    [string]$ModelName = "qwen2.5-3b-finance",
    [string]$RunId = "runB-r16-lr2e4"
)

$ErrorActionPreference = "Stop"

Write-Host "Preparing to upload local adapter artifact..."

if (-not (Test-Path $LocalAdapterDir)) {
    throw "Local adapter directory not found: $LocalAdapterDir"
}

$RequiredFiles = @(
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer_config.json",
    "tokenizer.json",
    "README.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $LocalAdapterDir $File

    if (-not (Test-Path $Path)) {
        throw "Missing required adapter file: $Path"
    }

    Write-Host "Found required file: $File"
}

$S3Prefix = "models/$ModelName/$RunId/adapter"
$S3Uri = "s3://$BucketName/$S3Prefix/"

Write-Host ""
Write-Host "Uploading adapter artifact..."
Write-Host "Local: $LocalAdapterDir"
Write-Host "S3:    $S3Uri"

aws s3 sync $LocalAdapterDir $S3Uri `
    --region $Region `
    --exclude "checkpoint-*" `
    --exclude "checkpoint-*/*"

if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload adapter artifact to S3."
}

Write-Host ""
Write-Host "Adapter upload complete."
Write-Host $S3Uri