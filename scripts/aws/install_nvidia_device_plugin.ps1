param(
    [string]$Namespace = "nvidia"
)

Write-Host "Adding NVIDIA device plugin Helm repository..."
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update

Write-Host "Installing NVIDIA device plugin..."
helm upgrade --install nvdp nvdp/nvidia-device-plugin `
  --namespace $Namespace `
  --create-namespace `
  --set gfd.enabled=true `
  --set mofedEnabled=false

Write-Host "NVIDIA device plugin installation submitted."
Write-Host "Check status with:"
Write-Host "kubectl get pods -n $Namespace"