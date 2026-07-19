param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks",
    [string]$Namespace = "finance-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying Finance LLM API Ingress..."
Write-Host "Cluster: $ClusterName"
Write-Host "Region:  $Region"

aws eks update-kubeconfig `
    --region $Region `
    --name $ClusterName

if ($LASTEXITCODE -ne 0) {
    throw "Failed to update kubeconfig."
}

Write-Host "Checking AWS Load Balancer Controller..."

kubectl get deployment aws-load-balancer-controller -n kube-system | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "AWS Load Balancer Controller is not installed. Run scripts/aws/install_aws_load_balancer_controller.ps1 first."
}

Write-Host "Checking service..."

kubectl get svc finance-llm-api -n $Namespace | Out-Null

if ($LASTEXITCODE -ne 0) {
    throw "finance-llm-api service not found. Deploy Milestone 8 first."
}

Write-Host "Applying Ingress manifest..."

kubectl apply -f k8s/inference/finance-llm-ingress.yaml

if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply Ingress manifest."
}

Write-Host "Ingress applied."
Write-Host "It can take a few minutes for AWS to provision the ALB."
Write-Host ""
Write-Host "Check Ingress:"
Write-Host "kubectl get ingress -n $Namespace finance-llm-api"