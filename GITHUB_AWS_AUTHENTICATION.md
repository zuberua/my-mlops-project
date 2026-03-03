# How GitHub Actions Authenticates to AWS

Complete guide to understanding OIDC authentication between GitHub Actions and AWS.

---

## Quick Answer

**GitHub Actions authenticates to AWS using OIDC (OpenID Connect)** - a secure, token-based authentication that doesn't require storing AWS credentials.

### Key Files:

1. **GitHub Actions Workflows:**
   - `.github/workflows/model-build.yml` (lines 56-60)
   - `.github/workflows/model-deploy.yml` (lines 56-60, 144-148)

2. **AWS Infrastructure:**
   - `terraform/main.tf` (lines 95-125, 127-185)

---

## The Authentication Flow

### Step-by-Step Process

```
1. GitHub Actions Workflow Starts
   ↓
2. GitHub Issues JWT Token
   ↓
3. GitHub Actions Sends Token to AWS
   ↓
4. AWS OIDC Provider Validates Token
   ↓
5. AWS STS Issues Temporary Credentials
   ↓
6. GitHub Actions Uses Credentials to Access AWS
```

---

## Implementation Details

### 1. GitHub Actions Workflow Configuration

**File:** `.github/workflows/model-build.yml` (lines 56-60)

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
    role-session-name: GitHubActions-ModelBuild
```

**What this does:**
- Uses the official AWS GitHub Action for authentication
- Specifies which IAM role to assume (stored in GitHub Secrets)
- Sets the AWS region
- Names the session for audit tracking

**Required Permissions in Workflow:**
```yaml
permissions:
  id-token: write   # Required to request JWT token from GitHub
  contents: read    # Required to checkout code
```

**File:** `.github/workflows/model-build.yml` (lines 36-37)

---

### 2. AWS OIDC Provider Setup

**File:** `terraform/main.tf` (lines 187-203)

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 1 : 0
  
  url = "https://token.actions.githubusercontent.com"
  
  client_id_list = [
    "sts.amazonaws.com"
  ]
  
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
  
  tags = {
    Name = "GitHub Actions OIDC Provider"
  }
}
```

**What this does:**
- Creates an OIDC provider in AWS that trusts GitHub
- URL points to GitHub's OIDC endpoint
- Client ID is AWS STS (Security Token Service)
- Thumbprint validates GitHub's SSL certificate

**Important:** This only needs to be created once per AWS account.

---

### 3. IAM Role for GitHub Actions

**File:** `terraform/main.tf` (lines 95-125)

```hcl
resource "aws_iam_role" "github_actions_role" {
  name = "${var.project_name}-github-actions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:*"
          }
        }
      }
    ]
  })
  
  tags = {
    Name    = "GitHub Actions Role"
    Project = var.project_name
  }
}
```

**What this does:**
- Creates an IAM role that GitHub Actions can assume
- **Trust Policy (assume_role_policy):**
  - Allows the GitHub OIDC provider to assume this role
  - Uses `AssumeRoleWithWebIdentity` action
  - **Condition checks:**
    - `aud` (audience) must be "sts.amazonaws.com"
    - `sub` (subject) must match your GitHub repo pattern
      - Example: `repo:your-org/your-repo:*`
      - The `*` allows any branch/tag/PR

**Security:** The `sub` condition ensures only YOUR GitHub repository can assume this role.

---

### 4. IAM Permissions Policy

**File:** `terraform/main.tf` (lines 127-185)

```hcl
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "${var.project_name}-github-actions-policy"
  role = aws_iam_role.github_actions_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:CreatePipeline",
          "sagemaker:UpdatePipeline",
          "sagemaker:DescribePipeline",
          "sagemaker:StartPipelineExecution",
          "sagemaker:DescribePipelineExecution",
          "sagemaker:ListPipelineExecutionSteps",
          "sagemaker:CreateModel",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:CreateEndpoint",
          "sagemaker:UpdateEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:DeleteEndpoint",
          "sagemaker:ListModelPackages",
          "sagemaker:DescribeModelPackage",
          "sagemaker:UpdateModelPackage",
          "sagemaker:CreateModelPackageGroup",
          "sagemaker:DescribeModelPackageGroup"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.sagemaker_bucket.arn,
          "${aws_s3_bucket.sagemaker_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = aws_iam_role.sagemaker_execution_role.arn
      },
      {
        Effect = "Allow"
        Action = [
          "application-autoscaling:RegisterScalableTarget",
          "application-autoscaling:PutScalingPolicy"
        ]
        Resource = "*"
      }
    ]
  })
}
```

**What this does:**
- Defines what actions GitHub Actions can perform in AWS
- **SageMaker permissions:** Create/update pipelines, models, endpoints
- **S3 permissions:** Read/write to the SageMaker bucket only
- **IAM permissions:** Pass the SageMaker execution role to SageMaker services
- **Auto Scaling permissions:** Configure endpoint auto scaling

**Security:** Uses least privilege - only grants necessary permissions.

---

## Detailed Authentication Flow

### Phase 1: GitHub Actions Requests Token

```yaml
# In workflow file
permissions:
  id-token: write  # This enables JWT token request
```

When the workflow runs:
1. GitHub Actions requests a JWT token from GitHub's OIDC provider
2. GitHub generates a token containing:
   - Repository information (`repo:owner/repo:ref:refs/heads/main`)
   - Workflow information
   - Actor (who triggered the workflow)
   - Expiration time (typically 1 hour)

**Example JWT Token Claims:**
```json
{
  "aud": "sts.amazonaws.com",
  "sub": "repo:your-org/your-repo:ref:refs/heads/main",
  "iss": "https://token.actions.githubusercontent.com",
  "repository": "your-org/your-repo",
  "ref": "refs/heads/main",
  "sha": "abc123...",
  "workflow": "Model Build Pipeline",
  "actor": "username",
  "exp": 1234567890
}
```

---

### Phase 2: AWS Action Exchanges Token

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
```

The `aws-actions/configure-aws-credentials` action:
1. Retrieves the JWT token from GitHub
2. Calls AWS STS `AssumeRoleWithWebIdentity` API
3. Sends:
   - JWT token
   - Role ARN to assume
   - Session name

**AWS API Call:**
```bash
aws sts assume-role-with-web-identity \
  --role-arn arn:aws:iam::123456789012:role/github-actions-role \
  --role-session-name GitHubActions-ModelBuild \
  --web-identity-token <JWT_TOKEN> \
  --duration-seconds 3600
```

---

### Phase 3: AWS Validates Token

AWS performs these checks:
1. **Verify token signature** - Ensures token is from GitHub
2. **Check audience (`aud`)** - Must be "sts.amazonaws.com"
3. **Check subject (`sub`)** - Must match the condition in trust policy
4. **Check expiration** - Token must not be expired
5. **Verify issuer** - Must be GitHub's OIDC provider

**Trust Policy Validation:**
```json
{
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
    },
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:*"
    }
  }
}
```

---

### Phase 4: AWS Issues Temporary Credentials

If validation succeeds, AWS STS returns:
```json
{
  "Credentials": {
    "AccessKeyId": "ASIA...",
    "SecretAccessKey": "...",
    "SessionToken": "...",
    "Expiration": "2024-02-03T01:00:00Z"
  },
  "AssumedRoleUser": {
    "AssumedRoleId": "AROA...:GitHubActions-ModelBuild",
    "Arn": "arn:aws:sts::123456789012:assumed-role/github-actions-role/GitHubActions-ModelBuild"
  }
}
```

**Key Points:**
- Credentials are **temporary** (typically 1 hour)
- Credentials are **scoped** to the IAM role's permissions
- Credentials **automatically expire**
- No long-lived credentials stored anywhere

---

### Phase 5: GitHub Actions Uses Credentials

The action automatically sets environment variables:
```bash
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export AWS_REGION="us-east-1"
```

All subsequent AWS CLI/SDK calls in the workflow use these credentials:
```yaml
- name: Create SageMaker Pipeline
  run: |
    python pipelines/create_pipeline.py  # Uses AWS credentials automatically
```

---

## Security Benefits

### 1. No Long-Lived Credentials
❌ **Old Way (Access Keys):**
```yaml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```
- Keys stored in GitHub Secrets
- Keys valid indefinitely
- If leaked, attacker has permanent access
- Need manual rotation

✅ **New Way (OIDC):**
```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
```
- No credentials stored
- Tokens valid for 1 hour only
- If leaked, attacker has limited time
- Automatic rotation

---

### 2. Scoped Access

**Repository-Specific:**
```hcl
"token.actions.githubusercontent.com:sub" = "repo:your-org/your-repo:*"
```
- Only YOUR repository can assume the role
- Other repositories cannot use your role
- Even if they know the role ARN

**Branch-Specific (Optional):**
```hcl
"token.actions.githubusercontent.com:sub" = "repo:your-org/your-repo:ref:refs/heads/main"
```
- Only the `main` branch can assume the role
- Feature branches cannot access production

---

### 3. Audit Trail

Every action is logged in AWS CloudTrail:
```json
{
  "eventName": "AssumeRoleWithWebIdentity",
  "userIdentity": {
    "type": "WebIdentityUser",
    "principalId": "arn:aws:sts::123456789012:assumed-role/github-actions-role/GitHubActions-ModelBuild",
    "userName": "GitHubActions-ModelBuild"
  },
  "requestParameters": {
    "roleArn": "arn:aws:iam::123456789012:role/github-actions-role",
    "roleSessionName": "GitHubActions-ModelBuild"
  },
  "sourceIPAddress": "140.82.112.0",
  "userAgent": "aws-actions/configure-aws-credentials"
}
```

You can see:
- Who assumed the role (GitHub Actions)
- When it happened
- From which IP address
- What session name was used

---

## Configuration Variables

### GitHub Secrets Required

**AWS_ROLE_ARN:**
```
arn:aws:iam::123456789012:role/mlops-demo-github-actions-role
```
- The ARN of the IAM role to assume
- Set in GitHub repository settings → Secrets and variables → Actions

**SAGEMAKER_EXECUTION_ROLE_ARN:**
```
arn:aws:iam::123456789012:role/mlops-demo-sagemaker-execution-role
```
- The ARN of the SageMaker execution role
- Passed to SageMaker services

---

### Terraform Variables

**File:** `terraform/terraform.tfvars`

```hcl
# GitHub repository information
github_org  = "your-org"
github_repo = "your-repo"

# AWS configuration
aws_region  = "us-east-1"
project_name = "mlops-demo"

# OIDC provider
create_github_oidc_provider = true  # Set to false if already exists
```

---

## Setup Instructions

### Step 1: Deploy AWS Infrastructure

```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

This creates:
- ✅ OIDC provider (if needed)
- ✅ IAM role for GitHub Actions
- ✅ IAM role for SageMaker
- ✅ S3 bucket
- ✅ Model package group

---

### Step 2: Get Role ARN

```bash
terraform output github_actions_role_arn
# Output: arn:aws:iam::123456789012:role/mlops-demo-github-actions-role

terraform output sagemaker_execution_role_arn
# Output: arn:aws:iam::123456789012:role/mlops-demo-sagemaker-execution-role
```

---

### Step 3: Add Secrets to GitHub

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add:
   - Name: `AWS_ROLE_ARN`
   - Value: `arn:aws:iam::123456789012:role/mlops-demo-github-actions-role`
4. Add:
   - Name: `SAGEMAKER_EXECUTION_ROLE_ARN`
   - Value: `arn:aws:iam::123456789012:role/mlops-demo-sagemaker-execution-role`

---

### Step 4: Test Authentication

Push code to trigger workflow:
```bash
git add .
git commit -m "Test OIDC authentication"
git push origin main
```

Check workflow logs for:
```
✓ Configure AWS credentials
  Assuming role: arn:aws:iam::123456789012:role/mlops-demo-github-actions-role
  Role assumed successfully
```

---

## Troubleshooting

### Error: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Cause:** Trust policy doesn't allow your repository

**Fix:** Check trust policy in IAM role:
```hcl
"token.actions.githubusercontent.com:sub" = "repo:YOUR-ORG/YOUR-REPO:*"
```

Make sure `YOUR-ORG` and `YOUR-REPO` match exactly.

---

### Error: "No OIDC provider found"

**Cause:** OIDC provider not created in AWS

**Fix:** Create OIDC provider:
```bash
cd terraform/
terraform apply -var="create_github_oidc_provider=true"
```

Or create manually in AWS Console:
- IAM → Identity providers → Add provider
- Provider type: OpenID Connect
- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

---

### Error: "Token expired"

**Cause:** Workflow took longer than 1 hour

**Fix:** Re-authenticate in long-running workflows:
```yaml
- name: Configure AWS credentials (again)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
```

---

### Error: "Access denied" when calling SageMaker

**Cause:** IAM role doesn't have required permissions

**Fix:** Add permissions to IAM policy in `terraform/main.tf`:
```hcl
Action = [
  "sagemaker:CreatePipeline",
  "sagemaker:UpdatePipeline",
  # Add more as needed
]
```

---

## Advanced Configuration

### Branch-Specific Roles

**Production role (main branch only):**
```hcl
Condition = {
  StringEquals = {
    "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
    "token.actions.githubusercontent.com:sub" = "repo:your-org/your-repo:ref:refs/heads/main"
  }
}
```

**Development role (all branches):**
```hcl
Condition = {
  StringEquals = {
    "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
  }
  StringLike = {
    "token.actions.githubusercontent.com:sub" = "repo:your-org/your-repo:*"
  }
}
```

---

### Multiple AWS Accounts

**Staging account:**
```yaml
- name: Configure AWS credentials (staging)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::111111111111:role/staging-role
    aws-region: us-east-1
```

**Production account:**
```yaml
- name: Configure AWS credentials (production)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::222222222222:role/production-role
    aws-region: us-east-1
```

---

## Comparison: OIDC vs Access Keys

| Aspect | OIDC (Recommended) | Access Keys (Legacy) |
|--------|-------------------|---------------------|
| **Security** | ✅ Temporary tokens | ❌ Long-lived keys |
| **Storage** | ✅ No credentials stored | ❌ Keys in GitHub Secrets |
| **Rotation** | ✅ Automatic (1 hour) | ❌ Manual rotation needed |
| **Scope** | ✅ Repository-specific | ❌ Account-wide |
| **Audit** | ✅ Full CloudTrail logs | ⚠️ Limited visibility |
| **Leak Risk** | ✅ Low (expires quickly) | ❌ High (permanent access) |
| **Setup** | ⚠️ More complex | ✅ Simple |
| **Best Practice** | ✅ Yes | ❌ No |

---

## Summary

### How It Works (Simple)
1. GitHub Actions requests a token from GitHub
2. GitHub Actions sends token to AWS
3. AWS validates token and issues temporary credentials
4. GitHub Actions uses credentials to access AWS services
5. Credentials expire after 1 hour

### Key Files
- **Workflows:** `.github/workflows/model-build.yml`, `.github/workflows/model-deploy.yml`
- **Infrastructure:** `terraform/main.tf`

### Key Components
- **OIDC Provider:** Trusts GitHub tokens
- **IAM Role:** Defines what GitHub Actions can do
- **Trust Policy:** Controls who can assume the role
- **Permissions Policy:** Controls what actions are allowed

### Security Benefits
- ✅ No long-lived credentials
- ✅ Automatic rotation
- ✅ Repository-specific access
- ✅ Complete audit trail
- ✅ Temporary credentials only

---

## Related Documentation

- [AWS IAM OIDC Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Security best practices
