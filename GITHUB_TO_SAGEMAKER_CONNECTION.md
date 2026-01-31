# How GitHub Actions Connects to SageMaker

## Overview

GitHub Actions connects to AWS SageMaker using **OIDC (OpenID Connect)** authentication - a secure, keyless method that doesn't require storing AWS credentials in GitHub.

## The Connection Flow

### Visual Diagram

![GitHub to SageMaker Connection](generated-diagrams/github-sagemaker-oidc-connection.png)

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLETE CONNECTION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

1. GitHub Actions Workflow Starts
         ↓
2. Request JWT Token from GitHub OIDC
         ↓
3. GitHub Issues JWT Token (signed)
         ↓
4. Send Token to AWS OIDC Provider
         ↓
5. AWS Validates Token & Trust Policy
         ↓
6. AWS STS Issues Temporary Credentials (15 min - 12 hours)
         ↓
7. Use Credentials to Call SageMaker API
         ↓
8. SageMaker Executes Operations
```

## Detailed Step-by-Step

### Step 1: GitHub Actions Workflow Starts

When you push code or manually trigger a workflow:

```yaml
# .github/workflows/model-build.yml
name: Model Build Pipeline

on:
  push:
    branches:
      - main

jobs:
  build-and-train:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # ← CRITICAL: Allows requesting OIDC token
      contents: read
```

**Key Point:** `id-token: write` permission is required to request OIDC tokens.

---

### Step 2: Request AWS Credentials

The workflow uses the official AWS action to configure credentials:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: us-east-1
    role-session-name: GitHubActions-ModelBuild
```

**What happens:**
1. Action requests JWT token from GitHub OIDC endpoint
2. GitHub generates a signed JWT token containing:
   - Repository name
   - Workflow name
   - Branch/tag
   - Actor (who triggered)
   - Expiration time

---

### Step 3: GitHub Issues JWT Token

GitHub's OIDC provider (`token.actions.githubusercontent.com`) issues a JWT token:

```json
{
  "iss": "https://token.actions.githubusercontent.com",
  "sub": "repo:your-org/your-repo:ref:refs/heads/main",
  "aud": "sts.amazonaws.com",
  "exp": 1234567890,
  "iat": 1234567800,
  "repository": "your-org/your-repo",
  "workflow": "Model Build Pipeline",
  "ref": "refs/heads/main",
  "sha": "abc123...",
  "actor": "username"
}
```

**Key Fields:**
- `sub` (subject): Identifies the repository and branch
- `aud` (audience): Must be `sts.amazonaws.com`
- `exp` (expiration): Token validity period

---

### Step 4: Send Token to AWS

The action sends the JWT token to AWS STS (Security Token Service):

```
POST https://sts.amazonaws.com/
Action=AssumeRoleWithWebIdentity
RoleArn=arn:aws:iam::ACCOUNT-ID:role/GitHubActionsRole
WebIdentityToken=<JWT_TOKEN>
RoleSessionName=GitHubActions-ModelBuild
```

---

### Step 5: AWS Validates Token

AWS performs multiple validation checks:

#### 5.1: OIDC Provider Validation

AWS checks if the OIDC provider exists and is trusted:

```hcl
# Created by Terraform
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = [
    "sts.amazonaws.com"
  ]
  
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
}
```

#### 5.2: Trust Policy Validation

AWS checks the IAM role's trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:*"
        }
      }
    }
  ]
}
```

**Validation Checks:**
- ✅ Token is signed by GitHub
- ✅ Token hasn't expired
- ✅ Audience matches `sts.amazonaws.com`
- ✅ Subject matches repository pattern
- ✅ OIDC provider is trusted

---

### Step 6: AWS STS Issues Temporary Credentials

If validation passes, AWS STS returns temporary credentials:

```json
{
  "Credentials": {
    "AccessKeyId": "ASIA...",
    "SecretAccessKey": "...",
    "SessionToken": "...",
    "Expiration": "2024-01-30T12:00:00Z"
  },
  "AssumedRoleUser": {
    "AssumedRoleId": "AROA...:GitHubActions-ModelBuild",
    "Arn": "arn:aws:sts::ACCOUNT-ID:assumed-role/GitHubActionsRole/GitHubActions-ModelBuild"
  }
}
```

**Credentials are:**
- ✅ Temporary (expire in 1 hour by default)
- ✅ Scoped to the role's permissions
- ✅ Automatically rotated on each workflow run
- ✅ Never stored in GitHub

---

### Step 7: Use Credentials to Call SageMaker

The action automatically configures AWS SDK with these credentials:

```yaml
- name: Create SageMaker Pipeline
  run: |
    python pipelines/create_pipeline.py \
      --region us-east-1 \
      --role ${{ secrets.SAGEMAKER_EXECUTION_ROLE_ARN }}
```

**Behind the scenes:**

```python
import boto3

# AWS SDK automatically uses credentials from environment
# No need to explicitly pass credentials!
sm_client = boto3.client('sagemaker', region_name='us-east-1')

# Call SageMaker API
response = sm_client.create_pipeline(
    PipelineName='mlops-demo-pipeline',
    RoleArn='arn:aws:iam::ACCOUNT-ID:role/SageMakerExecutionRole',
    # ... pipeline definition
)
```

**Environment Variables Set:**
```bash
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_REGION=us-east-1
```

---

### Step 8: SageMaker Executes Operations

SageMaker receives the API call and:

1. **Validates IAM permissions:**
   - Checks if GitHub Actions role has `sagemaker:CreatePipeline`
   - Checks if it can pass the SageMaker execution role

2. **Executes the operation:**
   - Creates the pipeline
   - Starts training jobs
   - Deploys endpoints
   - etc.

3. **Returns response:**
   - Pipeline ARN
   - Execution status
   - Error messages (if any)

---

## IAM Permissions Flow

### GitHub Actions Role Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreatePipeline",
        "sagemaker:UpdatePipeline",
        "sagemaker:StartPipelineExecution",
        "sagemaker:CreateEndpoint",
        "sagemaker:UpdateEndpoint"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::ACCOUNT-ID:role/SageMakerExecutionRole"
    }
  ]
}
```

**Key Permission:** `iam:PassRole` allows GitHub Actions to tell SageMaker to use the SageMaker execution role.

### SageMaker Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**This role is used BY SageMaker** to:
- Access S3 buckets
- Write CloudWatch logs
- Access ECR images
- etc.

---

## Security Benefits

### 1. No Long-Lived Credentials

**Traditional approach (BAD):**
```yaml
# ❌ DON'T DO THIS
env:
  AWS_ACCESS_KEY_ID: AKIA...
  AWS_SECRET_ACCESS_KEY: ...
```

**OIDC approach (GOOD):**
```yaml
# ✅ DO THIS
permissions:
  id-token: write
```

### 2. Automatic Rotation

- Credentials expire after 1 hour
- New credentials on each workflow run
- No manual rotation needed

### 3. Scoped Access

- Credentials only work for specific repository
- Can restrict to specific branches
- Can restrict to specific workflows

### 4. Audit Trail

Every API call is logged with:
- Who triggered the workflow
- Which repository
- Which branch
- Timestamp

---

## Configuration in Terraform

Here's how the connection is set up:

```hcl
# 1. Create OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = ["sts.amazonaws.com"]
  
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
}

# 2. Create GitHub Actions Role
resource "aws_iam_role" "github_actions_role" {
  name = "GitHubActionsRole"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:your-org/your-repo:*"
        }
      }
    }]
  })
}

# 3. Attach Permissions
resource "aws_iam_role_policy" "github_actions_policy" {
  role = aws_iam_role.github_actions_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sagemaker:*",
        "s3:*",
        "iam:PassRole"
      ]
      Resource = "*"
    }]
  })
}
```

---

## Workflow Configuration

### In GitHub Actions Workflow

```yaml
name: Model Build Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    # STEP 1: Grant permission to request OIDC token
    permissions:
      id-token: write
      contents: read
    
    steps:
      # STEP 2: Configure AWS credentials using OIDC
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
          role-session-name: GitHubActions-Build
      
      # STEP 3: Now you can use AWS services!
      - name: Create SageMaker Pipeline
        run: |
          aws sagemaker create-pipeline \
            --pipeline-name my-pipeline \
            --role-arn ${{ secrets.SAGEMAKER_EXECUTION_ROLE_ARN }}
```

### In GitHub Secrets

Add these secrets to your repository:

```
AWS_ROLE_ARN = arn:aws:iam::123456789012:role/GitHubActionsRole
SAGEMAKER_EXECUTION_ROLE_ARN = arn:aws:iam::123456789012:role/SageMakerExecutionRole
```

---

## Troubleshooting

### Error: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Cause:** Trust policy doesn't match repository

**Fix:**
```bash
# Check trust policy
aws iam get-role --role-name GitHubActionsRole

# Verify subject pattern matches your repo
"token.actions.githubusercontent.com:sub": "repo:YOUR-ORG/YOUR-REPO:*"
```

### Error: "OIDC provider not found"

**Cause:** OIDC provider not created

**Fix:**
```bash
# Create OIDC provider
terraform apply

# Or manually
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Error: "Access denied" when calling SageMaker

**Cause:** GitHub Actions role lacks permissions

**Fix:**
```bash
# Check role permissions
aws iam get-role-policy \
  --role-name GitHubActionsRole \
  --policy-name GitHubActionsPolicy

# Add missing permissions
```

---

## Comparison: OIDC vs Access Keys

| Aspect | OIDC (Recommended) | Access Keys (Not Recommended) |
|--------|-------------------|-------------------------------|
| **Security** | ✅ Temporary credentials | ❌ Long-lived credentials |
| **Rotation** | ✅ Automatic | ❌ Manual |
| **Exposure Risk** | ✅ Low | ❌ High |
| **Audit Trail** | ✅ Detailed | ⚠️ Limited |
| **Setup** | ⚠️ Moderate | ✅ Simple |
| **Maintenance** | ✅ None | ❌ Regular rotation needed |

---

## Summary

**How GitHub Actions connects to SageMaker:**

1. ✅ **Request OIDC token** from GitHub
2. ✅ **Send token to AWS** STS
3. ✅ **AWS validates** token and trust policy
4. ✅ **Receive temporary credentials** (1 hour)
5. ✅ **Call SageMaker API** with credentials
6. ✅ **SageMaker executes** operations

**Key Benefits:**
- 🔒 No AWS keys stored in GitHub
- 🔄 Automatic credential rotation
- 🎯 Scoped to specific repository
- 📊 Complete audit trail
- ⚡ Seamless integration

**This is the modern, secure way to connect CI/CD to AWS!**
