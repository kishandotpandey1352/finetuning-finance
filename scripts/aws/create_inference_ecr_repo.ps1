param(
    [string]$Region = "us-east-1",
    [string]$RepositoryName = "finance-llm-platform-inference"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking ECR repository: $RepositoryName"

$repoExists = $false

try {
    aws ecr describe-repositories `
        --region $Region `
        --repository-names $RepositoryName 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $repoExists = $true
    }
} catch {
    $repoExists = $false
}

if ($repoExists) {
    Write-Host "ECR repository already exists: $RepositoryName"
} else {
    Write-Host "Creating ECR repository: $RepositoryName"

    aws ecr create-repository `
        --region $Region `
        --repository-name $RepositoryName `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create ECR repository."
    }
}

$RepositoryUri = aws ecr describe-repositories `
    --region $Region `
    --repository-names $RepositoryName `
    --query "repositories[0].repositoryUri" `
    --output text

Write-Host "ECR repository ready:"
Write-Host $RepositoryUri