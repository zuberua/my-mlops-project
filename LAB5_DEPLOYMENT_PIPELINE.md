# Lab 5: Deployment Pipeline with GitHub Actions

This lab demonstrates the **automated deployment pipeline** using GitHub Actions instead of CodePipeline/CodeBuild.

## What This Lab Creates

An automated deployment pipeline that:
1. ✅ Detects approved models in Model Registry
2. ✅ Deploys to staging environment automatically
3. ✅ Runs automated tests on staging
4. ✅ Requires manual approval for production
5. ✅ Deploys to production with autoscaling
6. ✅ Enables Model Monitor

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              DEPLOYMENT PIPELINE FLOW                        │
└─────────────────────────────────────────────────────────────┘

Model Approved in Registry
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  GitHub Actions: Deploy Staging Job                        │
├────────────────────────────────────────────────────────────┤
│  1. Get Latest Approved Model                              │
│  2. Create Model from Model Package                        │
│  3. Create Endpoint Configuration                          │
│     - Instance: ml.m5.xlarge                               │
│     - Count: 1                                             │
│     - Data Capture: Enabled                                │
│  4. Create/Update Endpoint                                 │
│  5. Wait for InService (timeout: 15 min)                   │
│  6. Run Automated Tests                                    │
│     - Latency tests                                        │
│     - Accuracy tests                                       │
│     - Load tests                                           │
│  7. Upload Test Results                                    │
└────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  Manual Approval Gate (GitHub Environment)                 │
├────────────────────────────────────────────────────────────┤
│  • Review staging test results                             │
│  • Check model metrics                                     │
│  • Verify endpoint performance                             │
│  • Approve or reject deployment                            │
└────────────────────────────────────────────────────────────┘
         │
         ▼ (After Approval)
┌────────────────────────────────────────────────────────────┐
│  GitHub Actions: Deploy Production Job                     │
├────────────────────────────────────────────────────────────┤
│  1. Validate Staging Test Results                          │
│     - Accuracy >= 0.85                                     │
│     - Latency < 1000ms                                     │
│  2. Get Latest Approved Model                              │
│  3. Create Model from Model Package                        │
│  4. Create Endpoint Configuration                          │
│     - Instance: ml.m5.2xlarge                              │
│     - Count: 2 (min) to 10 (max)                           │
│     - Autoscaling: Enabled                                 │
│     - Data Capture: Enabled                                │
│  5. Create/Update Endpoint                                 │
│  6. Wait for InService (timeout: 20 min)                   │
│  7. Run Smoke Tests                                        │
│  8. Enable Model Monitor                                   │
│     - Schedule: Hourly                                     │
│     - Metrics: CloudWatch                                  │
│  9. Send Notifications (Slack)                             │
└────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Deployment Workflow (`.github/workflows/model-deploy.yml`)

**Triggers:**
- Successful completion of model build workflow
- Manual trigger with model package ARN
- Repository dispatch event (for external triggers)

**Jobs:**
- `deploy-staging` - Automatic deployment to staging
- `deploy-production` - Manual approval + production deployment

### 2. Deployment Scripts

**`deployment/deploy_endpoint.py`**
- Creates SageMaker model from model package
- Creates endpoint configuration with data capture
- Creates or updates endpoint
- Configures autoscaling (production only)

**`deployment/wait_endpoint.py`**
- Waits for endpoint to reach InService status
- Polls every 30 seconds
- Configurable timeout

### 3. Testing Scripts

**`tests/test_endpoint.py`**
- Invokes endpoint with test data
- Measures latency (avg, p50, p95, p99)
- Validates predictions
- Calculates accuracy
- Generates test report

**`tests/test_data.json`**
- Sample test cases
- Expected outputs
- Edge cases

### 4. Validation Scripts

**`scripts/validate_tests.py`**
- Validates staging test results
- Checks accuracy threshold
- Checks latency threshold
- Fails deployment if criteria not met

### 5. Monitoring Setup

**`monitoring/setup_monitor.py`**
- Creates Model Monitor schedule
- Configures hourly monitoring
- Enables CloudWatch metrics
- Sets up data quality checks

## Deployment Configuration

### Staging Environment

```yaml
Environment: staging
Instance Type: ml.m5.xlarge
Instance Count: 1
Autoscaling: Disabled
Data Capture: Enabled (100%)
Approval: Not required
```

### Production Environment

```yaml
Environment: production
Instance Type: ml.m5.2xlarge
Instance Count: 2-10 (autoscaling)
Autoscaling: Enabled
  - Target: 70 invocations/instance
  - Scale out: 60 seconds
  - Scale in: 300 seconds
Data Capture: Enabled (100%)
Model Monitor: Enabled (hourly)
Approval: Required (manual)
```

## GitHub Environment Setup

### Create Staging Environment

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `staging`
4. No protection rules needed
5. Save

### Create Production Environment

1. Click **New environment**
2. Name: `production`
3. Enable **Required reviewers**
4. Add reviewers (yourself or team)
5. Optional: Add deployment delay
6. Save

## Workflow Execution

### Automatic Trigger

When a model is approved in Model Registry:

```bash
# Model gets approved (manually or automatically)
aws sagemaker update-model-package \
  --model-package-arn <arn> \
  --model-approval-status Approved

# This triggers the deployment workflow automatically
```

### Manual Trigger

Deploy a specific model:

```bash
# Via GitHub UI:
# 1. Go to Actions → Model Deployment Pipeline
# 2. Click "Run workflow"
# 3. Enter model package ARN
# 4. Select environment (staging/production)
# 5. Click "Run workflow"
```

### Via GitHub CLI

```bash
gh workflow run model-deploy.yml \
  -f model_package_arn=arn:aws:sagemaker:... \
  -f environment=staging
```

## Testing Strategy

### Staging Tests (Automated)

**Functional Tests:**
- Endpoint responds correctly
- Predictions are valid
- Error handling works

**Performance Tests:**
- Latency < 1000ms (p95)
- Throughput adequate
- No timeouts

**Accuracy Tests:**
- Predictions match expected
- Accuracy >= 85%

### Production Tests (Smoke Tests)

**Basic Validation:**
- Endpoint is accessible
- Returns valid predictions
- Latency acceptable

**No Load Testing:**
- Production tests are minimal
- Real traffic validates performance

## Manual Approval Process

### Reviewer Checklist

Before approving production deployment:

1. **Review Staging Results**
   - Check test results artifact
   - Verify accuracy >= 85%
   - Verify latency < 1000ms

2. **Check Model Metrics**
   - Review training metrics
   - Check evaluation report
   - Verify model version

3. **Verify Staging Endpoint**
   - Test manually if needed
   - Check CloudWatch metrics
   - Review logs

4. **Approve Deployment**
   - Go to Actions → Workflow run
   - Click "Review deployments"
   - Select "production"
   - Add comment (optional)
   - Click "Approve and deploy"

### Approval Notifications

Reviewers receive:
- Email notification
- GitHub notification
- Slack message (if configured)

## Monitoring & Observability

### CloudWatch Metrics

**Endpoint Metrics:**
- `ModelLatency` - Inference latency
- `Invocations` - Total invocations
- `InvocationsPerInstance` - Load per instance
- `ModelSetupTime` - Cold start time

**Model Monitor Metrics:**
- `DataQualityViolations` - Data drift
- `ModelQualityViolations` - Model drift
- `FeatureBaseline` - Feature statistics

### GitHub Actions Logs

**Deployment Logs:**
- Model creation
- Endpoint configuration
- Endpoint status updates
- Test results
- Approval status

**Artifacts:**
- Test results JSON
- Deployment summary
- Model metadata

### Slack Notifications

**Production Deployments:**
```
🎉 Production Deployment Succeeded
Endpoint: mlops-demo-production
Model: arn:aws:sagemaker:...
Deployed by: @username
```

**Failures:**
```
❌ Production Deployment Failed
Endpoint: mlops-demo-production
Error: Endpoint creation failed
Check logs: [link]
```

## Rollback Strategy

### Automatic Rollback

Not implemented by default. Consider adding:

```yaml
- name: Rollback on Failure
  if: failure()
  run: |
    # Revert to previous endpoint configuration
    python scripts/rollback_endpoint.py \
      --endpoint-name mlops-demo-production
```

### Manual Rollback

```bash
# Get previous model version
aws sagemaker list-model-packages \
  --model-package-group-name mlops-demo-model-group \
  --sort-by CreationTime \
  --sort-order Descending

# Deploy previous version
gh workflow run model-deploy.yml \
  -f model_package_arn=<previous-arn> \
  -f environment=production
```

## Cost Optimization

### Staging Environment

**Stop when not needed:**
```bash
# Delete staging endpoint
aws sagemaker delete-endpoint \
  --endpoint-name mlops-demo-staging

# Recreate when needed (automatic via workflow)
```

**Use smaller instances:**
```yaml
--instance-type ml.t2.medium  # $0.065/hour
```

### Production Environment

**Use Spot Instances:**
```python
# In deploy_endpoint.py
ProductionVariants=[{
    "VariantName": "AllTraffic",
    "ModelName": model_name,
    "InstanceType": instance_type,
    "InitialInstanceCount": instance_count,
    "ManagedInstanceScaling": {
        "Status": "ENABLED",
        "MinInstanceCount": 2,
        "MaxInstanceCount": 10
    }
}]
```

**Enable Savings Plans:**
```bash
# 1-year commitment for 64% savings
aws savingsplans create-savings-plan \
  --savings-plan-type SageMaker \
  --commitment 100 \
  --upfront-payment-amount 0
```

## Troubleshooting

### Deployment Fails

**Issue:** Endpoint stuck in "Creating"

**Solution:**
```bash
# Check CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/mlops-demo-staging --follow

# Check endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name mlops-demo-staging
```

### Tests Fail

**Issue:** Accuracy below threshold

**Solution:**
```bash
# Review test results
# Download artifact from GitHub Actions
# Check test_results.json

# If model is actually good, adjust threshold:
# Edit scripts/validate_tests.py
--min-accuracy 0.80  # Lower threshold
```

### Approval Not Working

**Issue:** Can't approve deployment

**Solution:**
1. Verify you're added as reviewer in environment
2. Check environment protection rules
3. Ensure workflow is waiting for approval
4. Try refreshing GitHub page

### Autoscaling Not Working

**Issue:** Endpoint not scaling

**Solution:**
```bash
# Check autoscaling configuration
aws application-autoscaling describe-scalable-targets \
  --service-namespace sagemaker

# Check scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace sagemaker
```

## Best Practices

### 1. Always Test in Staging First
- Never deploy directly to production
- Run comprehensive tests in staging
- Validate with real-world scenarios

### 2. Use Manual Approval for Production
- Require at least one reviewer
- Add deployment delay (5-10 minutes)
- Document approval criteria

### 3. Monitor Everything
- Enable CloudWatch metrics
- Set up alarms for failures
- Monitor latency and throughput

### 4. Implement Gradual Rollout
- Use traffic shifting (A/B testing)
- Start with 10% traffic to new model
- Gradually increase if metrics are good

### 5. Have Rollback Plan
- Keep previous endpoint configuration
- Test rollback procedure
- Document rollback steps

## Lab 5 Checklist

- [ ] Deployment workflow created (`.github/workflows/model-deploy.yml`)
- [ ] Deployment scripts implemented (`deployment/`)
- [ ] Test scripts created (`tests/`)
- [ ] Validation scripts added (`scripts/`)
- [ ] Monitoring setup implemented (`monitoring/`)
- [ ] GitHub environments configured (staging, production)
- [ ] Manual approval enabled for production
- [ ] First deployment successful to staging
- [ ] Tests passed in staging
- [ ] Production deployment approved and successful
- [ ] Model Monitor enabled
- [ ] CloudWatch metrics visible

## Next Steps

After completing Lab 5:

1. **Lab 6: Add Model Monitoring** (Already included!)
   - Model Monitor is automatically enabled
   - Data capture is configured
   - CloudWatch metrics are available

2. **Lab 7: Implement A/B Testing**
   - Deploy multiple model variants
   - Split traffic between models
   - Compare performance

3. **Lab 8: Automated Retraining**
   - Trigger retraining on data drift
   - Schedule periodic retraining
   - Automate entire lifecycle

## Summary

Lab 5 demonstrates a **production-grade deployment pipeline** using GitHub Actions:

✅ **Automated** - No manual deployment steps
✅ **Safe** - Staging environment + manual approval
✅ **Tested** - Comprehensive automated tests
✅ **Monitored** - CloudWatch + Model Monitor
✅ **Scalable** - Autoscaling production endpoints
✅ **Auditable** - Complete history in GitHub

This replaces the AWS CodePipeline/CodeBuild deployment pipeline with a more flexible, cost-effective GitHub Actions solution!
