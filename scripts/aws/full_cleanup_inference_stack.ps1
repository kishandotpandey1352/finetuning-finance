param(
    [string]$Namespace = "finance-ai",
    [switch]$DeleteIngress,
    [switch]$DeleteApi,
    [switch]$ScaleCpuNodesToZero,
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks",
    [string]$CpuNodeGroupName = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Finance LLM cleanup started."

if ($DeleteIngress) {
    Write-Host "Deleting Ingress / ALB..."
    kubectl delete ingress finance-llm-api -n $Namespace --ignore-not-found=true
}

if ($DeleteApi) {
    Write-Host "Deleting API deployment, service, and secret..."
    kubectl delete deployment finance-llm-api -n $Namespace --ignore-not-found=true
    kubectl delete service finance-llm-api -n $Namespace --ignore-not-found=true
    kubectl delete secret finance-api-secret -n $Namespace --ignore-not-found=true
}

if ($ScaleCpuNodesToZero) {
    if ([string]::IsNullOrWhiteSpace($CpuNodeGroupName)) {
        throw "CpuNodeGroupName is required when using -ScaleCpuNodesToZero."
    }

    Write-Host "Scaling CPU node group to zero: $CpuNodeGroupName"

    aws eks update-nodegroup-config `
        --region $Region `
        --cluster-name $ClusterName `
        --nodegroup-name $CpuNodeGroupName `
        --scaling-config minSize=0,maxSize=3,desiredSize=0
}

Write-Host "Cleanup complete."