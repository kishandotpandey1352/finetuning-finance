param(
    [string]$Region = "us-east-1",
    [string]$BucketName = "finance-llm-local-artifacts-671607590681-us-east-1",
    [string]$ModelName = "qwen2.5-3b-finance",
    [string]$RunId = "runB-r16-lr2e4",
    [string]$LocalDir = "artifacts\qwen2.5-3b-finance\runB-r16-lr2e4\adapter"
)

$ErrorActionPreference = "Stop"

$S3Uri = "s3://$BucketName/models/$ModelName/$RunId/adapter/"

Write-Host "Downloading adapter artifact..."
Write-Host "S3:    $S3Uri"
Write-Host "Local: $LocalDir"

if (Test-Path $LocalDir) {
    Write-Host "Removing existing local directory: $LocalDir"
    Remove-Item -Recurse -Force $LocalDir
}

New-Item -ItemType Directory -Force $LocalDir | Out-Null

aws s3 sync $S3Uri $LocalDir --region $Region

if ($LASTEXITCODE -ne 0) {
    throw "Failed to download adapter artifact from S3."
}

Write-Host "Download complete."

$RequiredFiles = @(
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer_config.json",
    "tokenizer.json",
    "README.md"
)

foreach ($File in $RequiredFiles) {
    $Path = Join-Path $LocalDir $File

    if (-not (Test-Path $Path)) {
        throw "Missing downloaded file: $Path"
    }

    Write-Host "Found: $File"
}

Write-Host "Adapter downloaded and verified locally."