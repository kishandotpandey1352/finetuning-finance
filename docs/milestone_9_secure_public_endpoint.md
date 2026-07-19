# Milestone 9: Secure Public Endpoint and Monitoring Readiness

## Goal

Expose the Finance LLM FastAPI service through an AWS Application Load Balancer using Kubernetes Ingress.

The API remains protected using the `X-API-Key` header.

## Why Mock Mode Is Used

AWS GPU quota is unavailable, so the EKS API deployment runs with:

```text
USE_MOCK_MODEL=true