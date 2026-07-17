# Milestone 7: Inference Container and ECR Image

## Goal

Containerize the secure FastAPI inference service and push the image to Amazon ECR.

This milestone prepares the API for Kubernetes deployment in the next milestone.

## Main Files

```text
docker/inference/Dockerfile
docker/inference/requirements.txt
.dockerignore
scripts/aws/create_inference_ecr_repo.ps1
scripts/aws/build_and_push_inference_image.ps1
scripts/docker_run_inference_api_local.ps1