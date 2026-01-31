# Complete Setup Guide

Step-by-step guide to set up SageMaker MLOps with GitHub Actions.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] GitHub account and repository
- [ ] AWS CLI installed and configured
- [ ] Terraform installed (>= 1.0)
- [ ] Python 3.10+ installed
- [ ] Git installed

## Step 1: Prepare Your Repository

### 1.1 Create GitHub Repository

```bash
# Create new repository on GitHub
# Then clone it locally
git clone https://github.com/YOUR-ORG/YOUR-REPO.git
cd YOUR-REPO

# Copy all files from sagemaker-mlops-github/ to your repo
cp -r sagemaker-mlops-github/* .
```

### 1.2 Update Configuration

Edit `terraform/terraform.tfvars`:

```hcl
aws_region  = "us-east-1"  # Your preferred region
project_name = "my-mlops"   # Your project name
environment  = "dev"

github_org  = "your-github-org"      # Your GitHub org/username
github_repo = "your-repo-name"       # Your repo name

create_github_oidc_provider = true   # false if already exists
```

## Step 2: Deploy AWS Infrastructure

### 2.1 Initialize Terraform

```bash
cd terraform
terraform init
```

### 2.2 Review Plan

```bash
terraform plan
```

This will create:
- S3 bucket for SageMaker artifacts
- IAM role for SageMaker execution
- IAM role for GitHub Actions (with OIDC)
- Model Package Group
- GitHub OIDC provider (if needed)

### 2.3 Apply Infrastructure

```bash
terraform apply
# Type 'yes' to confirm
```

### 2.4 Save Outputs

```bash
# Save these values - you'll need them for GitHub secrets
terraform output github_actions_role_arn
terraform output sagemaker_execution_role_arn
terraform output sagemaker_bucket_name
```

## Step 3: Configure GitHub

### 3.1 Add Repository Secrets

Go to your GitHub repository:
1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

```
Name: AWS_ROLE_ARN
Value: <github_actions_role_arn from terraform output>

Name: SAGEMAKER_EXECUTION_ROLE_ARN
Value: <sagemaker_execution_role_arn from terraform output>
```

Optional (for Slack notifications):
```
Name: SLACK_WEBHOOK_URL
Value: <your-slack-webhook-url>
```

### 3.2 Create GitHub Environments

#### Create Staging Environment

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `staging`
4. Click **Configure environment**
5. No protection rules needed
6. Click **Save protection rules**

#### Create Production Environment

1. Click **New environment**
2. Name: `production`
3. Click **Configure environment**
4. Enable **Required reviewers**
5. Add yourself or team members as reviewers
6. Optional: Set deployment delay (e.g., 5 minutes)
7. Click **Save protection rules**

## Step 4: Verify GitHub Actions Permissions

### 4.1 Enable Workflow Permissions

1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

### 4.2 Verify OIDC Provider

```bash
# Check if OIDC provider exists
aws iam list-open-id-connect-providers

# Should see:
# arn:aws:iam::ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com
```

## Step 5: Test the Setup

### 5.1 Create Sample Data

Create a sample CSV file for testing:

```bash
# Create sample data in S3
cat > sample_data.csv << EOF
feature1,feature2,feature3,feature4,target
0.5,0.3,0.8,0.2,1
0.1,0.2,0.1,0.3,0
0.7,0.6,0.9,0.8,1
0.2,0.1,0.2,0.1,0
EOF

# Upload to S3
aws s3 cp sample_data.csv s3://$(terraform output -raw sagemaker_bucket_name)/my-mlops/input/data.csv
```

### 5.2 Trigger First Pipeline

```bash
# Commit and push to trigger workflow
git add .
git commit -m "Initial MLOps setup"
git push origin main
```

### 5.3 Monitor Workflow

1. Go to **Actions** tab in GitHub
2. Click on the running workflow
3. Watch the steps execute in real-time
4. Check for any errors

## Step 6: Verify Deployment

### 6.1 Check SageMaker Pipeline

```bash
# List pipelines
aws sagemaker list-pipelines

# Describe pipeline
aws sagemaker describe-pipeline \
  --pipeline-name my-mlops-pipeline
```

### 6.2 Check Model Registry

```bash
# List model packages
aws sagemaker list-model-packages \
  --model-package-group-name my-mlops-model-group
```

### 6.3 Check Staging Endpoint

```bash
# Describe endpoint
aws sagemaker describe-endpoint \
  --endpoint-name my-mlops-staging

# Test endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name my-mlops-staging \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt

cat output.txt
```

### 6.4 Approve Production Deployment

1. Go to **Actions** tab
2. Click on the deployment workflow
3. Click **Review deployments**
4. Select **production**
5. Click **Approve and deploy**

### 6.5 Check Production Endpoint

```bash
# Wait for deployment to complete
aws sagemaker describe-endpoint \
  --endpoint-name my-mlops-production

# Test production endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name my-mlops-production \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt
```

## Step 7: Customize for Your Use Case

### 7.1 Update Preprocessing

Edit `preprocessing/preprocess.py`:
- Add your data cleaning logic
- Feature engineering
- Handle missing values
- Encode categorical variables

### 7.2 Update Training

Edit `pipelines/create_pipeline.py`:
- Change algorithm (XGBoost, PyTorch, TensorFlow, etc.)
- Adjust hyperparameters
- Modify instance types

### 7.3 Update Evaluation

Edit `evaluation/evaluate.py`:
- Add custom metrics
- Adjust evaluation logic
- Change approval thresholds

### 7.4 Update Tests

Edit `tests/test_endpoint.py` and `tests/test_data.json`:
- Add more test cases
- Test edge cases
- Add performance tests

## Troubleshooting

### Issue: GitHub Actions can't assume AWS role

**Error:** `Not authorized to perform sts:AssumeRoleWithWebIdentity`

**Solution:**
```bash
# Check OIDC provider thumbprint
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com

# Verify trust policy
aws iam get-role --role-name my-mlops-github-actions-role
```

### Issue: Pipeline fails to create

**Error:** `AccessDeniedException`

**Solution:**
```bash
# Check GitHub Actions role permissions
aws iam get-role-policy \
  --role-name my-mlops-github-actions-role \
  --policy-name my-mlops-github-actions-policy
```

### Issue: Endpoint deployment fails

**Error:** `ResourceLimitExceeded`

**Solution:**
```bash
# Check service quotas
aws service-quotas get-service-quota \
  --service-code sagemaker \
  --quota-code L-D9E8B6F7

# Request quota increase if needed
```

### Issue: Model not auto-approved

**Solution:**
```bash
# Check evaluation results in GitHub Actions artifacts
# Ensure accuracy >= 0.8 threshold
# Manually approve if needed:
aws sagemaker update-model-package \
  --model-package-arn <arn> \
  --model-approval-status Approved
```

## Next Steps

1. **Add Real Data** - Replace sample data with your dataset
2. **Tune Hyperparameters** - Use SageMaker Automatic Model Tuning
3. **Add A/B Testing** - Deploy multiple model variants
4. **Setup Alerts** - Configure CloudWatch alarms
5. **Add Data Quality Monitoring** - Detect data drift
6. **Implement Retraining** - Automate model retraining
7. **Add Feature Store** - Centralize feature management

## Cleanup

To destroy all resources:

```bash
# Delete endpoints first
aws sagemaker delete-endpoint --endpoint-name my-mlops-staging
aws sagemaker delete-endpoint --endpoint-name my-mlops-production

# Wait for endpoints to be deleted
aws sagemaker wait endpoint-deleted --endpoint-name my-mlops-staging
aws sagemaker wait endpoint-deleted --endpoint-name my-mlops-production

# Destroy Terraform resources
cd terraform
terraform destroy
# Type 'yes' to confirm
```

## Support

- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## Success Checklist

- [ ] Infrastructure deployed with Terraform
- [ ] GitHub secrets configured
- [ ] GitHub environments created
- [ ] First pipeline executed successfully
- [ ] Model registered in Model Registry
- [ ] Staging endpoint deployed and tested
- [ ] Production deployment approved
- [ ] Production endpoint deployed and tested
- [ ] Model Monitor enabled

Congratulations! Your MLOps pipeline is now fully operational! 🎉
