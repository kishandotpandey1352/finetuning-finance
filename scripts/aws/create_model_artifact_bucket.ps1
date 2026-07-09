param(
    [string]$Region = "us-east-1",
    [string]$BucketName = "finance-llm-local-artifacts-671607590681-us-east-1"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking whether bucket exists: $BucketName"

$bucketExists = $false

try {
    aws s3api head-bucket --bucket $BucketName --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) {
        $bucketExists = $true
    }
} catch {
    $bucketExists = $false
}

if ($bucketExists) {
    Write-Host "Bucket already exists: $BucketName"
} else {
    Write-Host "Bucket does not exist or is not accessible. Creating bucket: $BucketName"

    if ($Region -eq "us-east-1") {
        aws s3api create-bucket `
            --bucket $BucketName `
            --region $Region
    } else {
        aws s3api create-bucket `
            --bucket $BucketName `
            --region $Region `
            --create-bucket-configuration LocationConstraint=$Region
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create bucket: $BucketName"
    }
}

Write-Host "Enabling bucket versioning..."

aws s3api put-bucket-versioning `
    --bucket $BucketName `
    --versioning-configuration Status=Enabled `
    --region $Region

if ($LASTEXITCODE -ne 0) {
    throw "Failed to enable bucket versioning."
}

Write-Host "Blocking public access..."

aws s3api put-public-access-block `
    --bucket $BucketName `
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true `
    --region $Region

if ($LASTEXITCODE -ne 0) {
    throw "Failed to block public access."
}

Write-Host "Bucket is ready."
Write-Host "s3://$BucketName"