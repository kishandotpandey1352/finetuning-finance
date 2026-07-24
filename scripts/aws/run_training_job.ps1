param(
    [string]$Namespace = "finance-ai",
    [string]$JobManifest = "k8s\training\llama3-finance-finetune-job.yaml"
)

$ErrorActionPreference = "Stop"

Write-Host "Applying namespace and service account manifests..."

kubectl apply -f k8s/namespaces.yaml
kubectl apply -f k8s/serviceaccounts/training-serviceaccount.yaml

Write-Host "Deleting previous training job if it exists..."

kubectl delete job llama3-finance-finetune -n $Namespace --ignore-not-found=true

Write-Host "Applying training job manifest..."

kubectl apply -f $JobManifest

Write-Host "Training job submitted."
Write-Host "Watch pod status:"
Write-Host "kubectl get pods -n $Namespace -w"
Write-Host ""
Write-Host "Watch logs after pod starts:"
Write-Host "kubectl logs -f job/llama3-finance-finetune -n $Namespace"