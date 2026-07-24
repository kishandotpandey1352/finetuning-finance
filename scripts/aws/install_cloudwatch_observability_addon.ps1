param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing or updating CloudWatch Observability add-on..."
Write-Host "Cluster: $ClusterName"
Write-Host "Region:  $Region"

$addonExists = $false

try {
    aws eks describe-addon `
        --region $Region `
        --cluster-name $ClusterName `
        --addon-name amazon-cloudwatch-observability 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $addonExists = $true
    }
} catch {
    $addonExists = $false
}

if ($addonExists) {
    Write-Host "CloudWatch Observability add-on already exists. Updating..."

    aws eks update-addon `
        --region $Region `
        --cluster-name $ClusterName `
        --addon-name amazon-cloudwatch-observability `
        --resolve-conflicts OVERWRITE | Out-Null
} else {
    Write-Host "Creating CloudWatch Observability add-on..."

    aws eks create-addon `
        --region $Region `
        --cluster-name $ClusterName `
        --addon-name amazon-cloudwatch-observability `
        --resolve-conflicts OVERWRITE | Out-Null
}

if ($LASTEXITCODE -ne 0) {
    throw "Failed to install or update CloudWatch Observability add-on."
}

Write-Host "CloudWatch Observability add-on submitted."
Write-Host "Check status with:"
Write-Host ".\scripts\aws\check_cloudwatch_observability.ps1"