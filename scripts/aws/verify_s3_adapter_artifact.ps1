param(
    [string]$Region = "us-east-1",
    [string]$BucketName = "finance-llm-local-artifacts-671607590681-us-east-1",
    [string]$ModelName = "qwen2.5-3b-finance",
    [string]$RunId = "runB-r16-lr2e4"
)

$ErrorActionPreference = "Stop"

$S3Prefix = "models/$ModelName/$RunId/adapter"
$S3Uri = "s3://$BucketName/$S3Prefix/"

Write-Host "Verifying adapter artifact in S3..."
Write-Host $S3Uri

$RequiredFiles = @(
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer_config.json",
    "tokenizer.json",
    "README.md"
)

foreach ($File in $RequiredFiles) {
    $Key = "$S3Prefix/$File"

    Write-Host "Checking s3://$BucketName/$Key"

    aws s3api head-object `
        --bucket $BucketName `
        --key $Key `
        --region $Region | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Missing required S3 object: s3://$BucketName/$Key"
    }

    Write-Host "Found: $File"
}

# Optional file. It exists in your local adapter folder, so warn if missing but do not fail.
$OptionalFiles = @(
    "chat_template.jinja"
)

foreach ($File in $OptionalFiles) {
    $Key = "$S3Prefix/$File"

    Write-Host "Checking optional file s3://$BucketName/$Key"

    aws s3api head-object `
        --bucket $BucketName `
        --key $Key `
        --region $Region 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Found optional file: $File"
    } else {
        Write-Warning "Optional file not found: $File"
    }
}

Write-Host ""
Write-Host "S3 adapter artifact verification complete."
Write-Host "Adapter is ready for inference loading."