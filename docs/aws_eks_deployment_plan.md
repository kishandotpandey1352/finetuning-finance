# AWS EKS Deployment Plan

## Project

Repo: `finetuning-finance`

Branch: `aws-eks-deployment`

## Goal

Build a production-style fine-tuned finance LLM platform on AWS EKS.

The platform will:

- Fine-tune Llama 3 on AWS EKS using QLoRA
- Save LoRA adapter artifacts and evaluation reports to Amazon S3
- Build and push training/inference containers to Amazon ECR
- Deploy secure FastAPI inference endpoints on EKS
- Expose endpoints through AWS ALB Ingress
- Use AWS Secrets Manager for sensitive values
- Use EKS Pod Identity or IAM Roles for Service Accounts for AWS permissions
- Monitor API and GPU metrics with Prometheus, Grafana, CloudWatch, and DCGM exporter
- Support manual training Jobs and scheduled CronJobs

## AWS Services

- Amazon EKS
- Amazon ECR
- Amazon S3
- AWS Secrets Manager
- Amazon CloudWatch
- AWS Load Balancer Controller
- IAM / EKS Pod Identity
- Prometheus
- Grafana
- NVIDIA DCGM exporter

## High-Level Architecture

```text
GitHub
  -> GitHub Actions
  -> Amazon ECR
  -> Amazon EKS

Amazon EKS
  -> Training Job / CronJob
      -> reads dataset from S3
      -> reads Hugging Face token from Secrets Manager
      -> fine-tunes Llama 3 with QLoRA
      -> evaluates the adapter
      -> uploads adapters and reports to S3

  -> Inference API Deployment
      -> loads Llama 3 base model
      -> loads selected LoRA adapter from S3
      -> exposes /summarize, /qa, /risk-analysis

  -> ALB Ingress
      -> HTTPS
      -> API key/JWT auth

  -> Monitoring
      -> Prometheus
      -> Grafana
      -> CloudWatch
      -> DCGM exporter