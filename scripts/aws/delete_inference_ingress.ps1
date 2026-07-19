param(
    [string]$Namespace = "finance-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "Deleting Finance LLM API Ingress..."

kubectl delete ingress finance-llm-api `
    -n $Namespace `
    --ignore-not-found=true

Write-Host "Ingress deleted."
Write-Host "AWS Load Balancer Controller should remove the ALB after a few minutes."