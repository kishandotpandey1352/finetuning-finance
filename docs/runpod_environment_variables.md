# RunPod Environment Variables

## Purpose

These variables configure the Finance LLM API to run real GPU-backed inference on RunPod.

## Required Variables

```text
USE_MOCK_MODEL=false
BASE_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
ADAPTER_S3_URI=s3://finance-llm-local-artifacts-671607590681-us-east-1/models/qwen2.5-3b-finance/runB-r16-lr2e4/adapter/
LOAD_IN_4BIT=true
DEVICE_MAP=auto
FINANCE_API_KEY=<api-key>
AWS_ACCESS_KEY_ID=<s3-readonly-access-key>
AWS_SECRET_ACCESS_KEY=<s3-readonly-secret-key>
AWS_DEFAULT_REGION=us-east-1