# Fix: OIDC Provider Already Exists

## The Error

```
Error: creating IAM OIDC Provider: EntityAlreadyExists: 
Provider with url https://token.actions.githubusercontent.com already exists.
```

## Why This Happens

You already created the GitHub OIDC provider when you set up the connection. Terraform is trying to create it again.

## Quick Fix

### Option 1: Edit terraform.tfvars (Recommended)

```bash
# Edit your terraform.tfvars file
nano terraform.tfvars
```

**Change this line:**
```hcl
create_github_oidc_provider = true
```

**To:**
```hcl
create_github_oidc_provider = false
```

**Save and run again:**
```bash
terraform apply
```

### Option 2: Import Existing Provider

If you want Terraform to manage the existing provider:

```bash
# Get the OIDC provider ARN
aws iam list-open-id-connect-providers

# Import it (replace ACCOUNT-ID with your account)
terraform import 'aws_iam_openid_connect_provider.github[0]' \
  arn:aws:iam::ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com

# Then run apply
terraform apply
```

## Complete terraform.tfvars Example

```hcl
aws_region  = "us-east-1"
project_name = "mlops-demo"
environment  = "dev"

# Your GitHub details
github_org  = "your-github-username"
github_repo = "your-repo-name"

# Set to false since you already created it!
create_github_oidc_provider = false
```

## Verify It Works

```bash
terraform plan
```

You should see:
```
Plan: 4 to add, 0 to change, 0 to destroy.
```

(Not 5, because OIDC provider already exists)

Then apply:
```bash
terraform apply
```
