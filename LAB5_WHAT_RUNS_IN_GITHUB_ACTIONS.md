# Lab 5: What Runs in GitHub Actions (Deployment Phase)

Complete breakdown of what executes in GitHub Actions during the deployment phase.

---

## Quick Answer

**GitHub Actions runs ORCHESTRATION only** - it coordinates the deployment but doesn't do the actual ML work.

### What Runs in GitHub Actions:
✅ Python scripts that call AWS APIs
✅ Deployment coordination
✅ Testing and validation
✅ Monitoring setup

### What Runs in AWS:
✅ SageMaker Endpoints (actual model serving)
✅ Model inference
✅ Auto scaling
✅ CloudWatch monitoring

---

## Lab 5 Deployment Workflow Breakdown

### File: `.github/workflows/model-deploy.yml`

---

## Job 1: Deploy to Staging (Automatic)

**Runs on:** GitHub Actions runner (ubuntu-latest, 2-4 cores, 7GB RAM)

### Step 1: Setup Environment
```yaml
- name: Checkout code
- name: Set up Python
- name: Install dependencies
```

**What runs:** 
- Git checkout
- Python 3.10 installation
- `pip install boto3 sagemaker`

**Where:** GitHub Actions runner
**Duration:** ~30 seconds
**Purpose:** Prepare environment for deployment scripts

---

### Step 2: Authenticate to AWS
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: us-east-1
```

**What runs:**
- OIDC token exchange with AWS
- Temporary credentials obtained (valid 1 hour)

**Where:** GitHub Actions runner → AWS STS
**Duration:** ~5 seconds
**Purpose:** Get temporary AWS credentials

---

### Step 3: Get Latest Approved Model
```yaml
- name: Get Latest Approved Model
  run: |
    python scripts/get_latest_model.py \
      --project-name mlops-demo \
      --region us-east-1 \
      --status Approved
```

**What runs:**
```python
# scripts/get_latest_model.py
import boto3

sagemaker = boto3.client('sagemaker')

# List model packages
response = sagemaker.list_model_packages(
    ModelPackageGroupName='mlops-demo-model-group',
    ModelApprovalStatus='Approved',
    SortBy='CreationTime',
    SortOrder='Descending'
)

# Get latest approved model
model_package_arn = response['ModelPackageSummaryList'][0]['ModelPackageArn']

# Save to file
with open('model_package_arn.txt', 'w') as f:
    f.write(model_package_arn)
```

**Where:** GitHub Actions runner (Python script)
**AWS API Calls:** `sagemaker:ListModelPackages`
**Duration:** ~2 seconds
**Purpose:** Find the latest approved model to deploy

---

### Step 4: Deploy to Staging
```yaml
- name: Deploy to Staging
  run: |
    python deployment/deploy_endpoint.py \
      --model-package-arn <ARN> \
      --endpoint-name mlops-demo-staging \
      --instance-type ml.m5.xlarge \
      --instance-count 1
```

**What runs:**
```python
# deployment/deploy_endpoint.py
import boto3

sagemaker = boto3.client('sagemaker')

# 1. Create Model
model_name = f'mlops-demo-staging-{timestamp}'
sagemaker.create_model(
    ModelName=model_name,
    PrimaryContainer={
        'ModelPackageName': model_package_arn
    },
    ExecutionRoleArn=execution_role_arn
)

# 2. Create Endpoint Config
config_name = f'mlops-demo-staging-config-{timestamp}'
sagemaker.create_endpoint_config(
    EndpointConfigName=config_name,
    ProductionVariants=[{
        'VariantName': 'AllTraffic',
        'ModelName': model_name,
        'InstanceType': 'ml.m5.xlarge',
        'InitialInstanceCount': 1
    }]
)

# 3. Create or Update Endpoint
try:
    sagemaker.update_endpoint(
        EndpointName='mlops-demo-staging',
        EndpointConfigName=config_name
    )
except:
    sagemaker.create_endpoint(
        EndpointName='mlops-demo-staging',
        EndpointConfigName=config_name
    )
```

**Where:** 
- **Script:** GitHub Actions runner
- **Endpoint:** AWS SageMaker (ml.m5.xlarge instance)

**AWS API Calls:**
- `sagemaker:CreateModel`
- `sagemaker:CreateEndpointConfig`
- `sagemaker:CreateEndpoint` or `sagemaker:UpdateEndpoint`

**Duration:** ~2 seconds (script execution)
**Purpose:** Trigger endpoint creation in AWS

**Important:** The script just TRIGGERS the deployment. The actual endpoint runs in AWS, not GitHub Actions.

---

### Step 5: Wait for Endpoint
```yaml
- name: Wait for Endpoint
  run: |
    python deployment/wait_endpoint.py \
      --endpoint-name mlops-demo-staging \
      --timeout 900
```

**What runs:**
```python
# deployment/wait_endpoint.py
import boto3
import time

sagemaker = boto3.client('sagemaker')

while True:
    response = sagemaker.describe_endpoint(
        EndpointName='mlops-demo-staging'
    )
    
    status = response['EndpointStatus']
    
    if status == 'InService':
        print("✓ Endpoint is ready!")
        break
    elif status in ['Failed', 'RollingBack']:
        raise Exception(f"Endpoint deployment failed: {status}")
    
    print(f"Status: {status}, waiting...")
    time.sleep(30)  # Check every 30 seconds
```

**Where:** GitHub Actions runner (polling script)
**AWS API Calls:** `sagemaker:DescribeEndpoint` (every 30 seconds)
**Duration:** ~8-10 minutes (waiting for AWS to provision endpoint)
**Purpose:** Wait until endpoint is ready

**What's happening in AWS during this time:**
1. AWS provisions ml.m5.xlarge instance
2. AWS downloads model from S3
3. AWS loads model into memory
4. AWS starts inference server
5. AWS runs health checks
6. Endpoint becomes "InService"

---

### Step 6: Test Staging Endpoint
```yaml
- name: Test Staging Endpoint
  run: |
    python tests/test_endpoint.py \
      --endpoint-name mlops-demo-staging \
      --test-data tests/test_data.json
```

**What runs:**
```python
# tests/test_endpoint.py
import boto3
import json

runtime = boto3.client('sagemaker-runtime')

# Load test data
with open('tests/test_data.json') as f:
    test_data = json.load(f)

# Invoke endpoint
response = runtime.invoke_endpoint(
    EndpointName='mlops-demo-staging',
    ContentType='text/csv',
    Body=test_data['input']
)

# Parse prediction
prediction = json.loads(response['Body'].read())

# Validate prediction
assert 'predictions' in prediction
assert len(prediction['predictions']) > 0
assert 0 <= prediction['predictions'][0] <= 1

# Save results
results = {
    'status': 'passed',
    'predictions': prediction['predictions'],
    'latency_ms': response['ResponseMetadata']['HTTPHeaders']['x-amzn-invoked-production-variant']
}

with open('test_results.json', 'w') as f:
    json.dump(results, f)
```

**Where:** 
- **Script:** GitHub Actions runner
- **Inference:** AWS SageMaker endpoint

**AWS API Calls:** `sagemaker-runtime:InvokeEndpoint`
**Duration:** ~5 seconds
**Purpose:** Validate endpoint works correctly

---

### Step 7: Upload Test Results
```yaml
- name: Upload Test Results
  uses: actions/upload-artifact@v4
  with:
    name: staging-test-results
    path: test_results.json
```

**What runs:** GitHub Actions artifact upload
**Where:** GitHub Actions
**Duration:** ~2 seconds
**Purpose:** Save test results for production job

---

### Step 8: Create Deployment Summary
```yaml
- name: Create Deployment Summary
  run: |
    cat >> $GITHUB_STEP_SUMMARY << EOF
    ## 🚀 Staging Deployment Complete
    
    **Endpoint Name:** mlops-demo-staging
    **Model Package:** arn:aws:sagemaker:...
    **Instance Type:** ml.m5.xlarge
    **Test Status:** success
    EOF
```

**What runs:** Markdown summary generation
**Where:** GitHub Actions
**Duration:** ~1 second
**Purpose:** Display summary in GitHub UI

---

## Job 2: Deploy to Production (After Manual Approval)

**Runs on:** GitHub Actions runner (ubuntu-latest)

**Requires:** Manual approval in GitHub UI

---

### Step 1-3: Setup (Same as Staging)
```yaml
- Checkout code
- Set up Python
- Install dependencies
- Configure AWS credentials
```

**Duration:** ~30 seconds

---

### Step 4: Download Staging Test Results
```yaml
- name: Download Staging Test Results
  uses: actions/download-artifact@v4
```

**What runs:** Download artifact from staging job
**Where:** GitHub Actions
**Duration:** ~2 seconds

---

### Step 5: Validate Staging Tests
```yaml
- name: Validate Staging Tests
  run: |
    python scripts/validate_tests.py \
      --test-results test_results.json \
      --min-accuracy 0.85
```

**What runs:**
```python
# scripts/validate_tests.py
import json

with open('test_results.json') as f:
    results = json.load(f)

if results['status'] != 'passed':
    raise Exception("Staging tests did not pass")

if results.get('accuracy', 0) < 0.85:
    raise Exception(f"Accuracy {results['accuracy']} below threshold 0.85")

print("✓ Staging tests validated successfully")
```

**Where:** GitHub Actions runner
**Duration:** ~1 second
**Purpose:** Ensure staging tests passed before production

---

### Step 6: Get Latest Approved Model
```yaml
- name: Get Latest Approved Model
  run: python scripts/get_latest_model.py
```

**Same as staging step 3**
**Duration:** ~2 seconds

---

### Step 7: Deploy to Production
```yaml
- name: Deploy to Production
  run: |
    python deployment/deploy_endpoint.py \
      --endpoint-name mlops-demo-production \
      --instance-type ml.m5.2xlarge \
      --instance-count 2 \
      --enable-autoscaling \
      --min-capacity 2 \
      --max-capacity 10
```

**What runs:**
```python
# deployment/deploy_endpoint.py
import boto3

sagemaker = boto3.client('sagemaker')
autoscaling = boto3.client('application-autoscaling')

# 1. Create Model (same as staging)
# 2. Create Endpoint Config
sagemaker.create_endpoint_config(
    EndpointConfigName=config_name,
    ProductionVariants=[{
        'VariantName': 'AllTraffic',
        'ModelName': model_name,
        'InstanceType': 'ml.m5.2xlarge',  # Larger instance
        'InitialInstanceCount': 2          # Multiple instances
    }]
)

# 3. Create/Update Endpoint
sagemaker.create_endpoint(...)

# 4. Configure Auto Scaling
autoscaling.register_scalable_target(
    ServiceNamespace='sagemaker',
    ResourceId=f'endpoint/{endpoint_name}/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    MinCapacity=2,
    MaxCapacity=10
)

autoscaling.put_scaling_policy(
    PolicyName=f'{endpoint_name}-scaling-policy',
    ServiceNamespace='sagemaker',
    ResourceId=f'endpoint/{endpoint_name}/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 70.0,
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        }
    }
)
```

**Where:**
- **Script:** GitHub Actions runner
- **Endpoint:** AWS SageMaker (ml.m5.2xlarge, 2-10 instances)

**AWS API Calls:**
- `sagemaker:CreateModel`
- `sagemaker:CreateEndpointConfig`
- `sagemaker:CreateEndpoint`
- `application-autoscaling:RegisterScalableTarget`
- `application-autoscaling:PutScalingPolicy`

**Duration:** ~3 seconds (script execution)

---

### Step 8: Wait for Endpoint
```yaml
- name: Wait for Endpoint
  run: python deployment/wait_endpoint.py --timeout 1200
```

**Same as staging, but longer timeout (20 minutes)**
**Duration:** ~10-15 minutes (waiting for AWS)

---

### Step 9: Smoke Test Production
```yaml
- name: Smoke Test Production
  run: python tests/test_endpoint.py
```

**Same as staging test**
**Duration:** ~5 seconds

---

### Step 10: Enable Model Monitor
```yaml
- name: Enable Model Monitor
  run: |
    python monitoring/setup_monitor.py \
      --endpoint-name mlops-demo-production
```

**What runs:**
```python
# monitoring/setup_monitor.py
import boto3

sagemaker = boto3.client('sagemaker')

# Create monitoring schedule
sagemaker.create_monitoring_schedule(
    MonitoringScheduleName=f'{endpoint_name}-monitor',
    MonitoringScheduleConfig={
        'ScheduleConfig': {
            'ScheduleExpression': 'cron(0 * * * ? *)'  # Every hour
        },
        'MonitoringJobDefinition': {
            'MonitoringInputs': [{
                'EndpointInput': {
                    'EndpointName': endpoint_name,
                    'LocalPath': '/opt/ml/processing/input'
                }
            }],
            'MonitoringOutputConfig': {
                'MonitoringOutputs': [{
                    'S3Output': {
                        'S3Uri': f's3://{bucket}/monitoring',
                        'LocalPath': '/opt/ml/processing/output'
                    }
                }]
            },
            'MonitoringResources': {
                'ClusterConfig': {
                    'InstanceCount': 1,
                    'InstanceType': 'ml.m5.xlarge',
                    'VolumeSizeInGB': 20
                }
            },
            'RoleArn': role_arn
        }
    }
)
```

**Where:**
- **Script:** GitHub Actions runner
- **Monitoring:** AWS SageMaker (runs hourly)

**AWS API Calls:** `sagemaker:CreateMonitoringSchedule`
**Duration:** ~2 seconds

---

### Step 11: Create Summary & Notify
```yaml
- name: Create Deployment Summary
- name: Notify Slack
```

**What runs:** Summary generation and Slack notification
**Where:** GitHub Actions
**Duration:** ~2 seconds

---

## Summary: What Runs Where

### GitHub Actions Runner (Orchestration)
✅ Python scripts (boto3 SDK calls)
✅ AWS API calls
✅ Waiting/polling
✅ Testing (sending requests)
✅ Validation logic
✅ Artifact management
✅ Summary generation

**Total Duration:** ~30-40 seconds of actual work
**Waiting Time:** ~20-25 minutes (waiting for AWS)

---

### AWS SageMaker (Actual ML Work)
✅ Model serving (inference)
✅ Endpoint provisioning
✅ Instance management
✅ Auto scaling
✅ Model monitoring
✅ Health checks

**Runs:** 24/7 until endpoint is deleted
**Cost:** ~$170/month per endpoint

---

## Key Insight

**GitHub Actions is just the ORCHESTRATOR** - it runs lightweight Python scripts that tell AWS what to do.

The actual heavy lifting (model serving, inference, scaling) happens in AWS SageMaker, not in GitHub Actions.

### Analogy:
- **GitHub Actions** = Project Manager (coordinates, monitors, reports)
- **AWS SageMaker** = Construction Workers (does the actual work)

---

## What Does NOT Run in GitHub Actions

❌ Model inference (runs in SageMaker endpoint)
❌ Model serving (runs in SageMaker endpoint)
❌ Auto scaling (managed by AWS)
❌ Model monitoring (runs in SageMaker)
❌ Health checks (managed by AWS)
❌ Load balancing (managed by AWS)

---

## Cost Breakdown

### GitHub Actions (Free Tier)
- Staging deployment: ~10 minutes
- Production deployment: ~15 minutes
- Total: ~25 minutes per deployment
- Cost: **$0** (within free tier)

### AWS SageMaker (Paid)
- Staging endpoint: ml.m5.xlarge × 1 = ~$170/month
- Production endpoint: ml.m5.2xlarge × 2-10 = ~$340-1700/month
- Total: **$510-1870/month**

**The real cost is in AWS, not GitHub Actions.**

---

## Comparison with AWS Workshop Lab 5

### Original Lab 5 (AWS CodePipeline)
```
AWS CodePipeline (orchestration)
    ↓
AWS CodeBuild (runs deployment scripts)
    ↓
AWS CloudFormation (creates resources)
    ↓
SageMaker Endpoints (model serving)
```

**Cost:** ~$50-100/month for CodePipeline + CodeBuild

### Our Implementation (GitHub Actions)
```
GitHub Actions (orchestration + runs scripts)
    ↓
SageMaker Endpoints (model serving)
```

**Cost:** $0/month for GitHub Actions

**Savings:** ~$50-100/month by using GitHub Actions instead of CodePipeline

---

## Related Documentation

- [LAB_DIAGRAMS.md](LAB_DIAGRAMS.md) - Visual diagrams
- [GITHUB_AWS_AUTHENTICATION.md](GITHUB_AWS_AUTHENTICATION.md) - How authentication works
- [GITHUB_ACTIONS_VS_SAGEMAKER_PIPELINE.md](GITHUB_ACTIONS_VS_SAGEMAKER_PIPELINE.md) - Training comparison
