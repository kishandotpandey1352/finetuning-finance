param(
    [string]$Region = "us-east-1",
    [string]$RepositoryName = "finance-llm-platform-inference",
    [string]$ImageTag = "v1"
)

$ErrorActionPreference = "Stop"

$AccountId = aws sts get-caller-identity --query Account --output text

if ([string]::IsNullOrWhiteSpace($AccountId)) {
    throw "Could not determine AWS account ID."
}

$Registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$ImageUri = "$Registry/${RepositoryName}:${ImageTag}"

Write-Host "Ensuring ECR repository exists..."

.\scripts\aws\create_inference_ecr_repo.ps1 `
    -Region $Region `
    -RepositoryName $RepositoryName

Write-Host "Logging in to ECR: $Registry"

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $Registry

if ($LASTEXITCODE -ne 0) {
    throw "Docker login to ECR failed."
}

Write-Host "Building inference image:"
Write-Host $ImageUri

docker build `
    -f docker/inference/Dockerfile `
    -t $ImageUri `
    .

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed."
}

Write-Host "Pushing inference image:"
Write-Host $ImageUri

docker push $ImageUri

if ($LASTEXITCODE -ne 0) {
    throw "Docker push failed."
}

Write-Host "Inference image pushed successfully:"
Write-Host $ImageUri