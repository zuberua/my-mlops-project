# Quick Reference Guide

## Common Commands

### Deploy Infrastructure
```bash
cd terraform
terraform init
terraform apply
```

### Trigger Pipeline Manually
```bash
# Via GitHub UI: Actions → Model Build Pipeline → Run workflow

# Or push code
git add .
git commit -m "Update model"
git push origin main
```

### Check Pipeline Status
```bash
aws sagemaker list-pipeline-executions \
  --pipeline-name mlops-demo-pipeline \
  --sort-by CreationTime \
  --sort-order Descending \
  --max-results 5
```

### List Models
```bash
aws sagemaker list-model-packages \
  --model-package-group-name mlops-demo-model-group \
  --sort-by CreationTime \
  --sort-order Descending
```

### Approve Model
```bash
aws sagemaker update-model-package \
  --model-package-arn <arn> \
  --model-approval-status Approved
```

### Check Endpoint Status
```bash
# Staging
aws sagemaker describe-endpoint --endpoint-name mlops-demo-staging

# Production
aws sagemaker describe-endpoint --endpoint-name mlops-demo-production
```

### Test Endpoint
```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name mlops-demo-production \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt && cat output.txt
```

### View Logs
```bash
# Pipeline logs
aws logs tail /aws/sagemaker/ProcessingJobs --follow

# Endpoint logs
aws logs tail /aws/sagemaker/Endpoints/mlops-demo-production --follow
```

### Delete Endpoint
```bash
aws sagemaker delete-endpoint --endpoint-name mlops-demo-staging
```

## GitHub Actions Workflows

### Model Build Workflow
- **File:** `.github/workflows/model-build.yml`
- **Triggers:** Push to main/develop, manual
- **Duration:** ~15-30 minutes
- **Outputs:** Model package ARN, metrics

### Model Deploy Workflow
- **File:** `.github/workflows/model-deploy.yml`
- **Triggers:** After successful build, manual
- **Duration:** ~10-20 minutes per environment
- **Requires:** Manual approval for production

## Key Thresholds

### Auto-Approval
- **Accuracy:** >= 0.8
- **Location:** `scripts/approve_model.py`

### Production Validation
- **Accuracy:** >= 0.85
- **Location:** `scripts/validate_tests.py`

### Model Evaluation
- **Condition:** Accuracy >= 0.8 to register
- **Location:** `pipelines/create_pipeline.py`

## Instance Types

### Training
- **Default:** ml.m5.xlarge
- **Cost:** ~$0.23/hour

### Processing
- **Default:** ml.m5.xlarge
- **Cost:** ~$0.23/hour

### Staging Endpoint
- **Default:** ml.m5.xlarge (1 instance)
- **Cost:** ~$0.23/hour

### Production Endpoint
- **Default:** ml.m5.2xlarge (2-10 instances)
- **Cost:** ~$0.46/hour per instance
- **Autoscaling:** Enabled

## S3 Bucket Structure

```
sagemaker-mlops-demo-{account-id}/
├── mlops-demo/
│   ├── input/
│   │   └── data.csv
│   ├── train/
│   ├── validation/
│   ├── test/
│   ├── models/
│   ├── evaluation/
│   └── data-capture/
│       ├── mlops-demo-staging/
│       └── mlops-demo-production/
└── monitoring/
    ├── mlops-demo-staging/
    └── mlops-demo-production/
```

## IAM Roles

### SageMaker Execution Role
- **Name:** `mlops-demo-sagemaker-execution-role`
- **Used by:** SageMaker pipelines, endpoints
- **Permissions:** SageMaker, S3, CloudWatch

### GitHub Actions Role
- **Name:** `mlops-demo-github-actions-role`
- **Used by:** GitHub Actions workflows
- **Auth:** OIDC (no keys needed)
- **Permissions:** SageMaker, S3, IAM PassRole

## Monitoring

### CloudWatch Metrics
- **Namespace:** AWS/SageMaker
- **Metrics:**
  - `ModelLatency`
  - `Invocations`
  - `InvocationsPerInstance`
  - `ModelSetupTime`

### Model Monitor
- **Schedule:** Hourly
- **Checks:** Data quality, model quality
- **Alerts:** CloudWatch alarms

## Cost Estimates (Monthly)

### Development (Staging Only)
- Training: ~$10-50 (on-demand)
- Staging endpoint: ~$170 (24/7)
- S3 storage: ~$5
- **Total:** ~$185-225/month

### Production
- Training: ~$10-50
- Staging endpoint: ~$170
- Production endpoint: ~$340-1,700 (2-10 instances)
- S3 storage: ~$10
- Data transfer: ~$10
- **Total:** ~$540-1,940/month

### Cost Optimization Tips
- Use Spot instances for training (-70%)
- Stop staging endpoint when not needed
- Use Serverless Inference for low traffic
- Enable SageMaker Savings Plans (-64%)

## Troubleshooting Quick Fixes

### Pipeline won't start
```bash
# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn $(terraform output -raw github_actions_role_arn) \
  --action-names sagemaker:CreatePipeline
```

### Endpoint stuck in "Creating"
```bash
# Check CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/mlops-demo-staging --follow
```

### GitHub Actions auth fails
```bash
# Verify OIDC provider
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn \
  arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/token.actions.githubusercontent.com
```

### Model not approved
```bash
# Check evaluation results
aws sagemaker describe-model-package \
  --model-package-name <arn> \
  --query 'ModelMetrics'
```

## Useful Links

- **SageMaker Console:** https://console.aws.amazon.com/sagemaker/
- **GitHub Actions:** https://github.com/YOUR-ORG/YOUR-REPO/actions
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/
- **S3 Bucket:** https://s3.console.aws.amazon.com/s3/buckets/

## Emergency Procedures

### Stop All Training Jobs
```bash
for job in $(aws sagemaker list-training-jobs --status-equals InProgress --query 'TrainingJobSummaries[*].TrainingJobName' --output text); do
  aws sagemaker stop-training-job --training-job-name $job
done
```

### Delete All Endpoints
```bash
for endpoint in $(aws sagemaker list-endpoints --query 'Endpoints[*].EndpointName' --output text); do
  aws sagemaker delete-endpoint --endpoint-name $endpoint
done
```

### Full Cleanup
```bash
# Run cleanup script
./cleanup.sh

# Or manually
cd terraform
terraform destroy
```
