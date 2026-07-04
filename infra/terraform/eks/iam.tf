resource "aws_iam_role" "training_pod" {
  name = "${local.name_prefix}-training-pod-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "training_pod" {
  name        = "${local.name_prefix}-training-pod-policy"
  description = "Permissions for EKS training pods."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.hf_token.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "training_pod" {
  role       = aws_iam_role.training_pod.name
  policy_arn = aws_iam_policy.training_pod.arn
}

resource "aws_iam_role" "inference_pod" {
  name = "${local.name_prefix}-inference-pod-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "inference_pod" {
  name        = "${local.name_prefix}-inference-pod-policy"
  description = "Permissions for EKS inference pods."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.hf_token.arn,
          aws_secretsmanager_secret.api_key.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "inference_pod" {
  role       = aws_iam_role.inference_pod.name
  policy_arn = aws_iam_policy.inference_pod.arn
}