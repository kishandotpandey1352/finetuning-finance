param(
    [string]$Namespace = "finance-ai",
    [string]$DeploymentName = "finance-llm-api"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking Finance LLM API Kubernetes health..."

Write-Host ""
Write-Host "Pods:"
kubectl get pods -n $Namespace -l app.kubernetes.io/name=finance-llm-api

Write-Host ""
Write-Host "Service:"
kubectl get svc -n $Namespace finance-llm-api

Write-Host ""
Write-Host "Deployment:"
kubectl get deployment -n $Namespace $DeploymentName

Write-Host ""
Write-Host "Rollout status:"
kubectl rollout status deployment/$DeploymentName -n $Namespace --timeout=60s

Write-Host ""
Write-Host "Recent logs:"
kubectl logs -n $Namespace deployment/$DeploymentName --tail=50

Write-Host ""
Write-Host "Health check complete."