param(
    [string]$Namespace = "finance-ai",
    [int]$LocalPort = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "Starting port-forward to Finance LLM API..."
Write-Host "Local URL: http://localhost:$LocalPort"

kubectl port-forward `
    -n $Namespace `
    service/finance-llm-api `
    "${LocalPort}:80"