param(
    [string]$Namespace = "finance-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "Removing Finance LLM API from EKS..."

kubectl delete deployment finance-llm-api -n $Namespace --ignore-not-found=true
kubectl delete service finance-llm-api -n $Namespace --ignore-not-found=true
kubectl delete secret finance-api-secret -n $Namespace --ignore-not-found=true

Write-Host "Finance LLM API removed."