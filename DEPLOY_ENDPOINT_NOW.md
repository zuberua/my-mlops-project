# Deploy Endpoint Now - Quick Guide

You have a trained model ready to deploy!

**Model:** `arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1`
**Status:** Approved ✅

---

## Quick Deploy (Recommended)

```bash
# 1. Refresh AWS credentials
isengardcli assume

# 2. Deploy endpoint
./deploy.sh
```

This will:
1. Create SageMaker model
2. Create endpoint config
3. Create endpoint (ml.m5.xlarge, 1 instance)
4. Wait for endpoint to be ready (~8-10 minutes)

---

## Alternative: Deploy via GitHub Actions

Go to GitHub Actions and manually trigger the deployment workflow:
1. Go to: https://github.com/YOUR-ORG/YOUR-REPO/actions
2. Click "Model Deployment Pipeline"
3. Click "Run workflow"
4. Enter model ARN: `arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1`
5. Select environment: `staging`
6. Click "Run workflow"

---

## Manual Commands (If Needed)

### Deploy Endpoint
```bash
export SAGEMAKER_EXECUTION_ROLE_ARN="arn:aws:iam::138720056246:role/mlops-demo-sagemaker-execution-role"

python3 deployment/deploy_endpoint.py \
  --model-package-arn "arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1" \
  --endpoint-name mlops-demo-staging \
  --instance-type ml.m5.xlarge \
  --instance-count 1 \
  --region us-east-1
```

### Wait for Endpoint
```bash
python3 deployment/wait_endpoint.py \
  --endpoint-name mlops-demo-staging \
  --region us-east-1 \
  --timeout 900
```

### Test Endpoint
```bash
python3 deployment/tests/test_endpoint.py \
  --endpoint-name mlops-demo-staging \
  --test-data deployment/tests/test_data.json \
  --region us-east-1
```

---

## Check Endpoint Status

```bash
aws sagemaker describe-endpoint --endpoint-name mlops-demo-staging
```

---

## What Gets Created

1. **SageMaker Model:** `mlops-demo-staging-model-{timestamp}`
2. **Endpoint Config:** `mlops-demo-staging-config-{timestamp}`
3. **Endpoint:** `mlops-demo-staging`
   - Instance: ml.m5.xlarge
   - Count: 1
   - Cost: ~$0.269/hour = ~$193/month

---

## Next Steps

After staging is deployed:

1. **Test the endpoint:**
   ```bash
   python deployment/tests/test_endpoint.py \
     --endpoint-name mlops-demo-staging \
     --test-data deployment/tests/test_data.json \
     --region us-east-1
   ```

2. **Deploy to production:**
   ```bash
   python deployment/deploy_endpoint.py \
     --model-package-arn "arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1" \
     --endpoint-name mlops-demo-production \
     --instance-type ml.m5.2xlarge \
     --instance-count 2 \
     --region us-east-1 \
     --enable-autoscaling \
     --min-capacity 2 \
     --max-capacity 10
   ```

---

## Troubleshooting

### Error: "No module named 'boto3'"
```bash
pip3 install boto3 sagemaker
```

### Error: "Unable to locate credentials"
Refresh your AWS credentials:
```bash
isengardcli assume
```

### Error: "Invalid approval status PendingManualApproval"
Approve the model first:
```bash
aws sagemaker update-model-package \
  --model-package-arn "arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1" \
  --model-approval-status Approved
```

### Error: "Endpoint already exists"
The script automatically handles updates - just run it again.

---

## Clean Up

To delete the endpoint:
```bash
aws sagemaker delete-endpoint --endpoint-name mlops-demo-staging
```

To delete endpoint config:
```bash
aws sagemaker delete-endpoint-config --endpoint-config-name mlops-demo-staging-config-{timestamp}
```

To delete model:
```bash
aws sagemaker delete-model --model-name mlops-demo-staging-model-{timestamp}
```
