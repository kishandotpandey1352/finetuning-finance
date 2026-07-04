output "aws_region" {
  value = var.aws_region
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "configure_kubectl" {
  value = "aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_name}"
}

output "artifact_bucket_name" {
  value = aws_s3_bucket.artifacts.bucket
}

output "training_ecr_repository_url" {
  value = aws_ecr_repository.training.repository_url
}

output "inference_ecr_repository_url" {
  value = aws_ecr_repository.inference.repository_url
}

output "hf_token_secret_arn" {
  value = aws_secretsmanager_secret.hf_token.arn
}

output "api_key_secret_arn" {
  value = aws_secretsmanager_secret.api_key.arn
}

output "training_pod_role_arn" {
  value = aws_iam_role.training_pod.arn
}

output "inference_pod_role_arn" {
  value = aws_iam_role.inference_pod.arn
}