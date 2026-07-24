param(
    [string]$Region = "us-east-1",
    [string]$TerraformDir = "infra\terraform\eks",
    [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "Reading ECR training repository URL from Terraform output..."

Push-Location $TerraformDir
$RepositoryUrl = terraform output -raw training_ecr_repository_url
Pop-Location

$Registry = $RepositoryUrl.Split("/")[0]
$ImageUri = "${RepositoryUrl}:${ImageTag}"

Write-Host "Logging in to ECR registry: $Registry"

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $Registry

Write-Host "Building training image: $ImageUri"

docker build `
  -f docker/training/Dockerfile `
  -t $ImageUri `
  .

Write-Host "Pushing training image: $ImageUri"

docker push $ImageUri

Write-Host "Training image pushed:"
Write-Host $ImageUri