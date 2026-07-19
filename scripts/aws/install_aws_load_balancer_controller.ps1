param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "finance-llm-platform-dev-eks",
    [string]$VpcId = "",
    [string]$PolicyName = "AWSLoadBalancerControllerIAMPolicy",
    [string]$RoleName = "finance-llm-platform-dev-alb-controller-role",
    [string]$Namespace = "kube-system",
    [string]$ServiceAccountName = "aws-load-balancer-controller"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing AWS Load Balancer Controller..."
Write-Host "Cluster: $ClusterName"
Write-Host "Region:  $Region"

$AccountId = (aws sts get-caller-identity --query "Account" --output text).Trim()

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($AccountId)) {
    throw "Could not determine AWS account ID. Run: aws sts get-caller-identity"
}

Write-Host "AWS Account ID: $AccountId"

Write-Host "Updating kubeconfig..."

aws eks update-kubeconfig `
    --region $Region `
    --name $ClusterName

if ($LASTEXITCODE -ne 0) {
    throw "Failed to update kubeconfig."
}

if ([string]::IsNullOrWhiteSpace($VpcId)) {
    Write-Host "Reading VPC ID from EKS cluster resources..."

    $VpcId = (aws eks describe-cluster `
        --region $Region `
        --name $ClusterName `
        --query "cluster.resourcesVpcConfig.vpcId" `
        --output text).Trim()
}

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($VpcId)) {
    throw "Could not determine VPC ID."
}

Write-Host "VPC ID: $VpcId"

$PolicyArn = "arn:aws:iam::${AccountId}:policy/$PolicyName"

Write-Host "Checking IAM policy: $PolicyArn"

$policyExists = $false

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

try {
    aws iam get-policy `
        --policy-arn $PolicyArn `
        --output json 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $policyExists = $true
    }
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if ($policyExists) {
    Write-Host "IAM policy already exists."
} else {
    Write-Host "IAM policy does not exist yet. It will be created."
    Write-Host "Downloading AWS Load Balancer Controller IAM policy..."

    $PolicyUrl = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json"
    $PolicyFile = Join-Path $env:TEMP "aws-load-balancer-controller-iam-policy.json"

    Invoke-WebRequest `
        -Uri $PolicyUrl `
        -OutFile $PolicyFile

    if (-not (Test-Path $PolicyFile)) {
        throw "Failed to download IAM policy file."
    }

    Write-Host "Creating IAM policy: $PolicyName"

    aws iam create-policy `
        --policy-name $PolicyName `
        --policy-document file://$PolicyFile | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create IAM policy."
    }
}

Write-Host "Getting EKS OIDC issuer..."

$OidcIssuer = (aws eks describe-cluster `
    --region $Region `
    --name $ClusterName `
    --query "cluster.identity.oidc.issuer" `
    --output text).Trim()

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($OidcIssuer)) {
    throw "Could not read OIDC issuer from EKS cluster."
}

$OidcProvider = $OidcIssuer -replace "https://", ""
$OidcProviderArn = "arn:aws:iam::${AccountId}:oidc-provider/$OidcProvider"

Write-Host "OIDC issuer:   $OidcIssuer"
Write-Host "OIDC provider: $OidcProviderArn"

Write-Host "Checking IAM OIDC provider..."

$oidcProviderExists = $false

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

try {
    aws iam get-open-id-connect-provider `
        --open-id-connect-provider-arn $OidcProviderArn `
        --output json 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $oidcProviderExists = $true
    }
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if (-not $oidcProviderExists) {
    throw "IAM OIDC provider does not exist for this cluster. Your Terraform EKS config must enable IRSA/OIDC provider creation."
}

$TrustPolicyFile = Join-Path $env:TEMP "aws-lbc-trust-policy.json"

@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "$OidcProviderArn"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OidcProvider}:aud": "sts.amazonaws.com",
          "${OidcProvider}:sub": "system:serviceaccount:${Namespace}:${ServiceAccountName}"
        }
      }
    }
  ]
}
"@ | Set-Content $TrustPolicyFile

$RoleArn = "arn:aws:iam::${AccountId}:role/$RoleName"

Write-Host "Checking IAM role: $RoleName"

$roleExists = $false

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

try {
    aws iam get-role `
        --role-name $RoleName `
        --output json 2>$null | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $roleExists = $true
    }
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if ($roleExists) {
    Write-Host "IAM role already exists."
} else {
    Write-Host "Creating IAM role: $RoleName"

    aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document file://$TrustPolicyFile | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create IAM role."
    }
}

Write-Host "Attaching IAM policy to role..."

aws iam attach-role-policy `
    --role-name $RoleName `
    --policy-arn $PolicyArn

if ($LASTEXITCODE -ne 0) {
    throw "Failed to attach IAM policy to role."
}

Write-Host "Creating or updating service account for controller..."

kubectl create serviceaccount $ServiceAccountName `
    -n $Namespace `
    --dry-run=client `
    -o yaml | kubectl apply -f -

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create or update Kubernetes service account."
}

kubectl annotate serviceaccount $ServiceAccountName `
    -n $Namespace `
    "eks.amazonaws.com/role-arn=$RoleArn" `
    --overwrite

if ($LASTEXITCODE -ne 0) {
    throw "Failed to annotate service account with IAM role."
}

Write-Host "Installing AWS Load Balancer Controller with Helm..."

helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller `
    -n $Namespace `
    --set clusterName=$ClusterName `
    --set region=$Region `
    --set vpcId=$VpcId `
    --set serviceAccount.create=false `
    --set serviceAccount.name=$ServiceAccountName

if ($LASTEXITCODE -ne 0) {
    throw "Helm install failed."
}

Write-Host "Waiting for controller rollout..."

kubectl rollout status deployment/aws-load-balancer-controller `
    -n $Namespace `
    --timeout=180s

if ($LASTEXITCODE -ne 0) {
    throw "AWS Load Balancer Controller rollout did not complete."
}

Write-Host ""
Write-Host "AWS Load Balancer Controller installed successfully."
Write-Host ""
Write-Host "Verify with:"
Write-Host "kubectl get deployment -n kube-system aws-load-balancer-controller"
Write-Host "kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller"