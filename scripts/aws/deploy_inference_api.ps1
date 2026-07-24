param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks",
    [string]$Namespace = "finance-ai",
    [string]$RepositoryName = "finance-llm-platform-inference",
    [string]$ImageTag = "v1",
    [string]$ApiKey = "dev-finance-api-key",
    [bool]$UseMockModel = $true
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying Finance LLM API to EKS..."
Write-Host "Cluster: $ClusterName"
Write-Host "Region:  $Region"
Write-Host "Mock:    $UseMockModel"

$AccountId = aws sts get-caller-identity --query Account --output text

if ([string]::IsNullOrWhiteSpace($AccountId)) {
    throw "Could not determine AWS account ID."
}

$ImageUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/${RepositoryName}:${ImageTag}"

Write-Host "Using image:"
Write-Host $ImageUri

Write-Host "Updating kubeconfig..."

aws eks update-kubeconfig `
    --region $Region `
    --name $ClusterName

if ($LASTEXITCODE -ne 0) {
    throw "Failed to update kubeconfig. Does the EKS cluster exist?"
}

Write-Host "Applying namespace..."

kubectl apply -f k8s/namespaces.yaml

Write-Host "Applying inference service account..."

kubectl apply -f k8s/serviceaccounts/inference-serviceaccount.yaml

Write-Host "Creating or updating API secret..."

kubectl create secret generic finance-api-secret `
    --namespace $Namespace `
    --from-literal=FINANCE_API_KEY=$ApiKey `
    --dry-run=client `
    -o yaml | kubectl apply -f -

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create or update Kubernetes secret."
}

Write-Host "Rendering deployment manifest..."

$TemplatePath = "k8s\inference\finance-llm-deployment.yaml"
$RenderedPath = "k8s\inference\finance-llm-deployment.rendered.yaml"

$MockValue = $UseMockModel.ToString().ToLower()

(Get-Content $TemplatePath -Raw) `
    -replace "IMAGE_URI_PLACEHOLDER", $ImageUri `
    -replace "USE_MOCK_MODEL_PLACEHOLDER", $MockValue |
    Set-Content $RenderedPath

Write-Host "Applying deployment..."

kubectl apply -f $RenderedPath

if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply deployment."
}

Write-Host "Applying service..."

kubectl apply -f k8s/inference/finance-llm-service.yaml

if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply service."
}

Write-Host "Waiting for deployment rollout..."

kubectl rollout status deployment/finance-llm-api -n $Namespace --timeout=180s

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Rollout did not complete within timeout. Check pods manually."
}

Write-Host ""
Write-Host "Deployment submitted."
Write-Host "Check pods:"
Write-Host "kubectl get pods -n $Namespace"
Write-Host ""
Write-Host "Port forward:"
Write-Host ".\scripts\aws\port_forward_inference_api.ps1"