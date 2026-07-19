param(
    [string]$Namespace = "finance-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "Reading Ingress endpoint..."

$Endpoint = kubectl get ingress finance-llm-api `
    -n $Namespace `
    -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"

if ([string]::IsNullOrWhiteSpace($Endpoint)) {
    Write-Warning "Ingress endpoint is not ready yet. Wait a few minutes and rerun."
    exit 1
}

Write-Host ""
Write-Host "Finance LLM API endpoint:"
Write-Host "http://$Endpoint"
Write-Host ""
Write-Host "Health:"
Write-Host "http://$Endpoint/health"