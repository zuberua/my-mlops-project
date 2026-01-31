# Step-by-Step Deployment Guide

Now that you've set up the GitHub to AWS connection, follow these steps to deploy the complete MLOps solution.

## Prerequisites Checklist

- [x] GitHub to AWS OIDC connection created
- [ ] AWS CLI configured
- [ ] Terraform installed
- [ ] Python 3.10+ installed
- [ ] GitHub repository created

## Step 1: Deploy AWS Infrastructure with Terraform

### 1.1 Navigate to Terraform Directory

```bash
cd sagemaker-mlops-github/terraform
```

### 1.2 Create terraform.tfvars File

```bash
cp terraform.tfvars.example terraform.tfvars
```

### 1.3 Edit terraform.tfvars

```bash
# Edit with your values
nano terraform.tfvars
```

**Required values:**
```hcl
aws_region  = "us-east-1"              # Your AWS region
project_name = "mlops-demo"             # Your project name
environment  = "dev"                    # Environment name

github_org  = "your-github-username"    # Your GitHub username or org
github_repo = "your-repo-name"          # Your repository name

# Set to false if OIDC provider already exists
create_github_oidc_provider = false     # You already created it!
```

### 1.4 Initialize Terraform

```bash
terraform init
```

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### 1.5 Review the Plan

```bash
terraform plan
```

**This will create:**
- S3 bucket for SageMaker artifacts
- IAM role for SageMaker execution
- IAM role for GitHub Actions (uses existing OIDC provider)
- SageMaker Model Package Group

### 1.6 Apply Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**Expected output:**
```
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
github_actions_role_arn = "arn:aws:iam::123456789012:role/mlops-demo-github-actions-role"
sagemaker_execution_role_arn = "arn:aws:iam::123456789012:role/mlops-demo-sagemaker-execution-role"
sagemaker_bucket_name = "sagemaker-us-east-1-123456789012"
model_package_group_name = "mlops-demo-model-group"
```

### 1.7 Save the Outputs

```bash
# Save outputs to a file for reference
terraform output > ../terraform-outputs.txt
```

---

## Step 2: Configure GitHub Repository

### 2.1 Add Repository Secrets

Go to your GitHub repository:
1. Click **Settings**
2. Click **Secrets and variables** → **Actions**
3. Click **New repository secret**

**Add these secrets:**

**Secret 1:**
```
Name: AWS_ROLE_ARN
Value: <copy from terraform output: github_actions_role_arn>
```

**Secret 2:**
```
Name: SAGEMAKER_EXECUTION_ROLE_ARN
Value: <copy from terraform output: sagemaker_execution_role_arn>
```

**Optional (for Slack notifications):**
```
Name: SLACK_WEBHOOK_URL
Value: <your-slack-webhook-url>
```

### 2.2 Create GitHub Environments

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
5. Add yourself as a reviewer
6. Optional: Set wait timer (e.g., 5 minutes)
7. Click **Save protection rules**

### 2.3 Enable Workflow Permissions

1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

---

## Step 3: Upload Sample Data to S3

### 3.1 Create Sample Training Data

```bash
cd ..  # Back to sagemaker-mlops-github/

# Create sample CSV data
cat > sample_data.csv << 'EOF'
feature1,feature2,feature3,feature4,target
0.5,0.3,0.8,0.2,1
0.1,0.2,0.1,0.3,0
0.7,0.6,0.9,0.8,1
0.2,0.1,0.2,0.1,0
0.6,0.5,0.7,0.6,1
0.3,0.4,0.3,0.4,0
0.8,0.7,0.9,0.9,1
0.1,0.1,0.2,0.2,0
0.9,0.8,0.95,0.85,1
0.15,0.25,0.15,0.35,0
EOF
```

### 3.2 Upload to S3

```bash
# Get bucket name from terraform output
BUCKET_NAME=$(cd terraform && terraform output -raw sagemaker_bucket_name)

# Upload sample data
aws s3 cp sample_data.csv s3://${BUCKET_NAME}/mlops-demo/input/data.csv

# Verify upload
aws s3 ls s3://${BUCKET_NAME}/mlops-demo/input/
```

**Expected output:**
```
2024-01-30 10:00:00        123 data.csv
```

---

## Step 4: Push Code to GitHub

### 4.1 Initialize Git Repository (if not already)

```bash
# If you haven't initialized git yet
git init
git add .
git commit -m "Initial MLOps setup"
```

### 4.2 Add Remote and Push

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git

# Push to main branch
git branch -M main
git push -u origin main
```

**This will automatically trigger the Model Build workflow!**

---

## Step 5: Monitor the Model Build Workflow

### 5.1 Watch Workflow Execution

1. Go to your GitHub repository
2. Click **Actions** tab
3. Click on the running workflow "Model Build Pipeline"
4. Watch the steps execute in real-time

**Expected steps:**
1. ✅ Checkout code
2. ✅ Set up Python
3. ✅ Install dependencies
4. ✅ Run tests
5. ✅ Configure AWS credentials (OIDC)
6. ✅ Create or Update SageMaker Pipeline
7. ✅ Start SageMaker Pipeline Execution
8. ✅ Wait for Pipeline Completion (~15-20 minutes)
9. ✅ Get Pipeline Results
10. ✅ Approve Model for Deployment

### 5.2 Check SageMaker Pipeline in AWS Console

```bash
# Or via CLI
aws sagemaker list-pipeline-executions \
  --pipeline-name mlops-demo-pipeline \
  --sort-by CreationTime \
  --sort-order Descending \
  --max-results 1
```

---

## Step 6: Monitor the Deployment Workflow

### 6.1 Watch Staging Deployment

After the build workflow completes, the deployment workflow starts automatically:

1. Go to **Actions** tab
2. Click on "Model Deployment Pipeline"
3. Watch staging deployment

**Staging steps:**
1. ✅ Get Latest Approved Model
2. ✅ Deploy to Staging Endpoint (~5-10 minutes)
3. ✅ Wait for InService
4. ✅ Run Automated Tests
5. ✅ Upload Test Results

### 6.2 Check Staging Endpoint

```bash
# Check endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name mlops-demo-staging

# Test endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name mlops-demo-staging \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt

cat output.txt
```

### 6.3 Approve Production Deployment

1. In the workflow run, you'll see "Waiting for approval"
2. Click **Review deployments**
3. Select **production**
4. Review the staging test results
5. Add a comment (optional)
6. Click **Approve and deploy**

### 6.4 Watch Production Deployment

**Production steps:**
1. ✅ Validate Staging Tests
2. ✅ Deploy to Production Endpoint (~10-15 minutes)
3. ✅ Wait for InService
4. ✅ Run Smoke Tests
5. ✅ Enable Model Monitor
6. ✅ Send Notifications

### 6.5 Check Production Endpoint

```bash
# Check endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name mlops-demo-production

# Test endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name mlops-demo-production \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt

cat output.txt
```

---

## Step 7: Verify Complete Deployment

### 7.1 Check All Resources

```bash
# List pipelines
aws sagemaker list-pipelines

# List model packages
aws sagemaker list-model-packages \
  --model-package-group-name mlops-demo-model-group

# List endpoints
aws sagemaker list-endpoints

# Check S3 bucket
aws s3 ls s3://${BUCKET_NAME}/mlops-demo/ --recursive
```

### 7.2 Check CloudWatch Metrics

```bash
# Get endpoint metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=mlops-demo-production \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### 7.3 Verify Model Monitor

```bash
# Check monitoring schedule
aws sagemaker list-monitoring-schedules \
  --endpoint-name mlops-demo-production
```

---

## Step 8: Test the Complete Pipeline

### 8.1 Make a Code Change

```bash
# Edit a file to trigger the pipeline
echo "# Updated" >> README.md
git add README.md
git commit -m "Test pipeline trigger"
git push origin main
```

### 8.2 Watch the Pipeline Run Again

1. Go to **Actions** tab
2. Watch the new workflow run
3. Verify it completes successfully

---

## Troubleshooting

### Issue: Workflow fails at "Configure AWS credentials"

**Error:** `Error: Not authorized to perform sts:AssumeRoleWithWebIdentity`

**Solution:**
```bash
# Check if OIDC provider exists
aws iam list-open-id-connect-providers

# Check trust policy
aws iam get-role --role-name mlops-demo-github-actions-role

# Verify the trust policy includes your repository
```

### Issue: Pipeline execution fails

**Error:** `AccessDeniedException`

**Solution:**
```bash
# Check GitHub Actions role permissions
aws iam get-role-policy \
  --role-name mlops-demo-github-actions-role \
  --policy-name mlops-demo-github-actions-policy

# Check SageMaker execution role
aws iam get-role --role-name mlops-demo-sagemaker-execution-role
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

### Issue: No data in S3

**Solution:**
```bash
# Re-upload sample data
aws s3 cp sample_data.csv s3://${BUCKET_NAME}/mlops-demo/input/data.csv
```

---

## Verification Checklist

- [ ] Terraform infrastructure deployed successfully
- [ ] GitHub secrets configured
- [ ] GitHub environments created (staging, production)
- [ ] Sample data uploaded to S3
- [ ] Code pushed to GitHub
- [ ] Model Build workflow completed successfully
- [ ] Model registered in Model Registry
- [ ] Staging endpoint deployed and tested
- [ ] Production deployment approved
- [ ] Production endpoint deployed and tested
- [ ] Model Monitor enabled
- [ ] CloudWatch metrics visible

---

## Next Steps

### 1. Customize the Pipeline

Edit these files for your use case:
- `preprocessing/preprocess.py` - Your data preprocessing logic
- `pipelines/create_pipeline.py` - Change algorithm, hyperparameters
- `evaluation/evaluate.py` - Your evaluation metrics
- `tests/test_data.json` - Your test cases

### 2. Add More Test Cases

```bash
# Edit test data
nano tests/test_data.json

# Add more samples
```

### 3. Setup CloudWatch Alarms

```bash
# Create alarm for high latency
aws cloudwatch put-metric-alarm \
  --alarm-name mlops-demo-high-latency \
  --alarm-description "Alert when latency is high" \
  --metric-name ModelLatency \
  --namespace AWS/SageMaker \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=EndpointName,Value=mlops-demo-production
```

### 4. Configure Slack Notifications

1. Create Slack webhook
2. Add to GitHub secrets as `SLACK_WEBHOOK_URL`
3. Notifications will be sent automatically

---

## Cost Management

### Current Costs

**Staging:**
- Endpoint: ml.m5.xlarge (~$0.23/hour = ~$170/month)

**Production:**
- Endpoint: ml.m5.2xlarge x2 (~$0.46/hour x2 = ~$680/month)

**Total:** ~$850/month

### Cost Optimization

**Stop staging when not needed:**
```bash
aws sagemaker delete-endpoint --endpoint-name mlops-demo-staging
```

**Use smaller instances:**
```bash
# Edit deployment/deploy_endpoint.py
--instance-type ml.t2.medium  # $0.065/hour
```

**Enable SageMaker Savings Plans:**
- 1-year commitment: 40% savings
- 3-year commitment: 64% savings

---

## Summary

You've successfully deployed:
- ✅ Complete MLOps infrastructure
- ✅ Automated model training pipeline
- ✅ Automated deployment pipeline
- ✅ Staging and production environments
- ✅ Model monitoring
- ✅ GitHub Actions CI/CD

**Your MLOps pipeline is now fully operational!** 🎉

For questions or issues, check:
- [SETUP_GUIDE.md](SETUP_GUIDE.md)
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- [GITHUB_TO_SAGEMAKER_CONNECTION.md](GITHUB_TO_SAGEMAKER_CONNECTION.md)
