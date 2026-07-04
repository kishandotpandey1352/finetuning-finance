# Milestone 3: EKS GPU Validation Runbook

## Goal

Validate that the AWS EKS cluster can run NVIDIA GPU workloads.

## Current Blocker

The GPU managed node group exists, but the AWS account currently has insufficient EC2 vCPU quota for G-family On-Demand instances in `us-east-1`.

The required quota is:

- Service: Amazon EC2
- Quota: Running On-Demand G and VT instances
- Minimum needed: 4 vCPUs for one `g5.xlarge`
- Recommended request: 8 vCPUs

## Completed Before Quota Approval

- EKS cluster is running
- CPU node group is running
- GPU node group exists
- Kubernetes namespace `finance-ai` created
- Kubernetes namespace `nvidia` created
- Training service account created
- Inference service account created
- EKS Pod Identity associations created
- NVIDIA device plugin install script added
- GPU smoke test manifest added

## After Quota Approval

### 1. Scale GPU Node Group to 1

```powershell
aws eks update-nodegroup-config `
  --region us-east-1 `
  --cluster-name finance-llm-platform-dev-eks `
  --nodegroup-name finllm-dev-gpu-2026070420135864050000001d `
  --scaling-config minSize=0,maxSize=1,desiredSize=1