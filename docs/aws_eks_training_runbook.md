# Milestone 4: Training on AWS EKS

## Goal

Run Llama 3 QLoRA fine-tuning on AWS EKS using a GPU-backed Kubernetes Job.

## Milestone 4 Scope

- Build training Docker image
- Push image to Amazon ECR
- Upload dataset to S3
- Run Kubernetes training Job
- Save LoRA adapter artifacts and reports to S3

## Important Status

The training Job is GPU-ready, but it cannot run until AWS GPU quota is available.

Current blocker:

- EC2 quota: Running On-Demand G and VT instances
- Required minimum: 4 vCPUs for one `g5.xlarge`
- Current account status: quota increase rejected by AWS Support

## Required AWS Resources

- EKS cluster
- GPU node group
- ECR training repository
- S3 artifact bucket
- Secrets Manager secret for Hugging Face token
- EKS Pod Identity association for `finance-training-sa`

## Dataset Layout in S3

```text
s3://<artifact-bucket>/datasets/finance_gold_train.jsonl
s3://<artifact-bucket>/datasets/finance_gold_test.jsonl