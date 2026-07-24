param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking CloudWatch Observability add-on..."

aws eks describe-addon `
    --region $Region `
    --cluster-name $ClusterName `
    --addon-name amazon-cloudwatch-observability `
    --query "addon.{Name:addonName,Status:status,Version:addonVersion,Health:health}" `
    --output table

Write-Host ""
Write-Host "Checking observability pods..."

kubectl get pods -A | Select-String "cloudwatch|amazon-cloudwatch|otel|fluent"