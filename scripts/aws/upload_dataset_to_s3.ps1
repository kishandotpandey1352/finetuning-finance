param(
    [string]$Region = "us-east-1",
    [string]$TerraformDir = "infra\terraform\eks",
    [string]$TrainFile = "data\instruction\finance_gold_train.jsonl",
    [string]$EvalFile = "data\instruction\finance_gold_test.jsonl"
)

$ErrorActionPreference = "Stop"

Write-Host "Reading artifact bucket from Terraform output..."

if (-not (Test-Path $TerraformDir)) {
    throw "Terraform directory not found: $TerraformDir"
}

Push-Location $TerraformDir

$BucketName = terraform output -raw artifact_bucket_name 2>$null

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($BucketName)) {
    Pop-Location
    throw "Could not read Terraform output 'artifact_bucket_name'. The infrastructure may not exist. Run 'terraform apply' first."
}

Pop-Location

$BucketName = $BucketName.Trim()

if ($BucketName -notmatch "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$") {
    throw "Invalid S3 bucket name from Terraform output: $BucketName"
}

if (-not (Test-Path $TrainFile)) {
    throw "Train file not found: $TrainFile"
}

if (-not (Test-Path $EvalFile)) {
    throw "Eval file not found: $EvalFile"
}

Write-Host "Using artifact bucket: $BucketName"

Write-Host "Uploading training dataset to s3://$BucketName/datasets/finance_gold_train.jsonl"
aws s3 cp $TrainFile "s3://$BucketName/datasets/finance_gold_train.jsonl" --region $Region

if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload training dataset."
}

Write-Host "Uploading eval dataset to s3://$BucketName/datasets/finance_gold_test.jsonl"
aws s3 cp $EvalFile "s3://$BucketName/datasets/finance_gold_test.jsonl" --region $Region

if ($LASTEXITCODE -ne 0) {
    throw "Failed to upload eval dataset."
}

Write-Host "Dataset upload complete."
Write-Host "Train: s3://$BucketName/datasets/finance_gold_train.jsonl"
Write-Host "Eval:  s3://$BucketName/datasets/finance_gold_test.jsonl"