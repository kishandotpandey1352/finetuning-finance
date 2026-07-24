# Milestone 8: EKS Inference Deployment

## Goal

Deploy the containerized Finance LLM FastAPI service to Amazon EKS.

Because AWS GPU quota is unavailable, the first EKS deployment uses mock mode. This validates Kubernetes deployment, service routing, API key security, health checks, and metrics without requiring GPU capacity.

## Main Files

```text
k8s/inference/finance-llm-deployment.yaml
k8s/inference/finance-llm-service.yaml
scripts/aws/deploy_inference_api.ps1
scripts/aws/port_forward_inference_api.ps1
scripts/aws/undeploy_inference_api.ps1