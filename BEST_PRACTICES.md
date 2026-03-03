# Best Practices: GitHub Actions + SageMaker Pipelines

## Why This Hybrid Approach?

### Quick Comparison

| Feature | Hybrid (Recommended) | GitHub Actions Only |
|---------|---------------------|---------------------|
| **Training Time** | Unlimited | 6 hours max |
| **GPU Support** | ✅ Any GPU | ❌ None |
| **Scalability** | ✅ Unlimited | ❌ Limited (2-4 cores) |
| **Cost (small)** | $0.07/run | $0 (free tier) |
| **Production Ready** | ✅ Yes | ❌ No |

### When to Use Each

**Hybrid (GitHub Actions + SageMaker):**
- Training > 30 minutes
- Datasets > 1GB
- Need GPUs
- Production workloads
- Team collaboration

**GitHub Actions Only:**
- Learning/prototyping
- Training < 10 minutes
- Datasets < 1GB
- Hobby projects

**Bottom Line:** For $7/month extra, you get unlimited scalability, GPU support, and production features.

---

## Architecture Principles

### Separation of Concerns

**GitHub Actions (CI/CD):**
- Code quality checks
- Unit tests
- Pipeline creation
- Deployment automation

**SageMaker Pipelines (ML):**
- Data preprocessing
- Model training
- Model evaluation
- Model registration

**Rule:** GitHub Actions orchestrates, SageMaker executes ML workloads.

---

## 1. Code Organization

**DO:**
- Separate workflows by purpose (build, deploy, test)
- Modular structure (pipelines/, preprocessing/, evaluation/)
- Infrastructure as code (terraform/)
- Comprehensive tests (tests/)

**DON'T:**
- One massive workflow file
- All code in one file
- Production code in notebooks
- Shell scripts everywhere

---

## 2. GitHub Actions Workflows

**DO:**
- Separate workflows: model-build.yml, model-deploy.yml, code-quality.yml
- Trigger on relevant paths only
- Use workflow dependencies (workflow_run)
- Add job summaries with metrics

**DON'T:**
- Put everything in one workflow
- Trigger on all changes
- Mix training and deployment
- Skip test jobs

---

## 3. SageMaker Pipeline Design

**DO:**
- Parameterize everything (instance types, data paths)
- Add conditional steps (accuracy thresholds)
- Implement retry logic for transient failures
- Use proper error handling
- Enable pipeline caching

**DON'T:**
- Hardcode values
- Skip error handling
- Ignore retry policies
- Use fixed configurations

---

## 4. Security

**DO:**
- Use OIDC (no long-lived credentials)
- Implement least privilege IAM policies
- Scope permissions to specific resources
- Use GitHub Secrets for sensitive data
- Enable CloudTrail for audit logs

**DON'T:**
- Store AWS access keys in GitHub
- Use wildcard permissions (Action: "*", Resource: "*")
- Share credentials across environments
- Commit secrets to code

---

## 5. Environment Management

**DO:**
- Use GitHub Environments (staging, production)
- Require manual approval for production
- Environment-specific configurations
- Separate IAM roles per environment
- Different instance types per environment

**DON'T:**
- Deploy directly to production
- Use same config for all environments
- Skip staging environment
- Share resources across environments

---

## 6. Testing Strategy

**DO:**
- Unit tests (run in GitHub Actions)
- Integration tests (after deployment)
- Pipeline validation tests
- Test before every deployment
- Fail fast on test failures

**DON'T:**
- Skip testing
- Test only in production
- Manual testing only
- Deploy without validation

---

## 7. Monitoring & Observability

**DO:**
- Track all metrics (accuracy, latency, errors)
- Set up CloudWatch alarms
- Enable detailed logging
- Add job summaries in GitHub Actions
- Monitor endpoint health

**DON'T:**
- Deploy without monitoring
- Ignore CloudWatch metrics
- Skip alerting setup
- Rely only on logs

---

## 8. Data Management

**DO:**
- Version your data (v20240101/)
- Validate data quality before training
- Store data in S3 with versioning
- Track data lineage
- Implement data validation steps

**DON'T:**
- Use unversioned data
- Skip data quality checks
- Store data locally
- Ignore data drift

---

## 9. Model Registry

**DO:**
- Register all models with metadata
- Add git commit hash to metadata
- Implement approval workflows
- Track model lineage
- Version models properly

**DON'T:**
- Skip model registry
- Deploy unregistered models
- Ignore model versioning
- Skip approval process

---

## 10. Deployment Strategies

**DO:**
- Use blue-green deployment
- Implement canary releases (10% → 50% → 100%)
- Gradual traffic shifting
- Easy rollback mechanism
- Test in staging first

**DON'T:**
- Deploy all traffic at once
- Skip canary testing
- Deploy without rollback plan
- Ignore staging results

---

## 11. Cost Optimization

**DO:**
- Use spot instances for training (70-90% savings)
- Enable autoscaling for endpoints
- Right-size instances per environment
- Stop unused endpoints
- Use SageMaker Savings Plans

**DON'T:**
- Use on-demand for everything
- Over-provision resources
- Run 24/7 staging endpoints
- Ignore cost monitoring

---

## 12. Common Anti-Patterns

**Avoid These Mistakes:**

1. **Training large models in GitHub Actions** - Use SageMaker instead
2. **Hardcoding secrets** - Use GitHub Secrets and OIDC
3. **Skipping tests** - Always test before deploy
4. **No staging environment** - Always test in staging first
5. **Wildcard IAM permissions** - Use least privilege
6. **No monitoring** - Set up CloudWatch alarms
7. **No rollback plan** - Always have a way back
8. **Manual deployments** - Automate everything
9. **No data versioning** - Version all data
10. **Ignoring costs** - Monitor and optimize

---

## The Golden Rules

1. **Separate Concerns** - GitHub Actions for CI/CD, SageMaker for ML
2. **Use OIDC** - No long-lived credentials
3. **Test Everything** - Unit, integration, pipeline tests
4. **Version Everything** - Code, data, models, infrastructure
5. **Monitor Everything** - Logs, metrics, alerts
6. **Automate Everything** - No manual production steps
7. **Secure Everything** - Least privilege, encryption, audit trails
8. **Cost Optimize** - Spot instances, autoscaling, right-sizing
9. **Stage First** - Always test in staging before production
10. **Document** - Architecture, procedures, runbooks

---

## Production Readiness Checklist

Before going to production:

**Security:**
- [ ] OIDC authentication configured
- [ ] Least privilege IAM policies
- [ ] No secrets in code
- [ ] CloudTrail enabled

**Environments:**
- [ ] Staging environment set up
- [ ] Production environment set up
- [ ] Manual approval for production
- [ ] Environment-specific configs

**Testing:**
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Pipeline validation tests
- [ ] Staging tests successful

**Monitoring:**
- [ ] CloudWatch alarms configured
- [ ] Endpoint monitoring enabled
- [ ] Cost alerts set up
- [ ] Log aggregation working

**ML Operations:**
- [ ] Data versioning implemented
- [ ] Model registry in use
- [ ] Model approval workflow
- [ ] Rollback procedure documented

**Cost:**
- [ ] Spot instances enabled
- [ ] Autoscaling configured
- [ ] Right-sized instances
- [ ] Cost monitoring active

**Documentation:**
- [ ] Architecture documented
- [ ] Runbook created
- [ ] Troubleshooting guide
- [ ] Team trained

---

## Key Metrics to Track

**Model Metrics:**
- Accuracy, Precision, Recall, F1, AUC
- Training time and cost
- Model size

**Endpoint Metrics:**
- Invocations per minute
- Model latency (p50, p95, p99)
- Error rates (4xx, 5xx)
- Instance utilization

**Pipeline Metrics:**
- Pipeline execution time
- Step success/failure rates
- Cost per execution

**Business Metrics:**
- Deployment frequency
- Time to production
- Mean time to recovery (MTTR)
- Cost per prediction

---

## Resources

- [AWS SageMaker Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/best-practices.html)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [MLOps Principles](https://ml-ops.org/content/mlops-principles)
- [AWS Well-Architected ML Lens](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/)

---

## Summary

**The hybrid approach (GitHub Actions + SageMaker Pipelines) is the best practice for production ML because:**

1. **Scalability** - Unlimited compute resources
2. **Flexibility** - Any instance type, GPU support
3. **Reliability** - Built-in retry, checkpointing
4. **Features** - Model registry, lineage tracking, monitoring
5. **Cost** - Spot instances, autoscaling
6. **Compliance** - Audit trails, encryption, governance
7. **Collaboration** - Multiple teams, parallel experiments

**Use GitHub Actions only for orchestration, not for ML workloads.**

## Architecture Principles

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (CI/CD Orchestration)                   │
│  - Code quality checks                                  │
│  - Unit tests                                           │
│  - Pipeline creation/updates                            │
│  - Deployment automation                                │
│  - Approval workflows                                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  SageMaker Pipelines (ML Workflow Execution)            │
│  - Data preprocessing                                   │
│  - Model training                                       │
│  - Model evaluation                                     │
│  - Model registration                                   │
└─────────────────────────────────────────────────────────┘
```

**Key Principle:** GitHub Actions orchestrates, SageMaker Pipelines executes ML workloads.

## 1. Code Organization

### ✅ DO: Modular Structure

```
project/
├── .github/workflows/          # CI/CD workflows
│   ├── model-build.yml         # Training pipeline
│   ├── model-deploy.yml        # Deployment pipeline
│   └── code-quality.yml        # Linting, tests
├── pipelines/                  # SageMaker Pipeline definitions
│   ├── create_pipeline.py      # Pipeline definition
│   ├── run_pipeline.py         # Execute pipeline
│   └── wait_pipeline.py        # Monitor execution
├── preprocessing/              # Data preprocessing code
│   └── preprocess.py
├── training/                   # Training code (if custom)
│   └── train.py
├── evaluation/                 # Evaluation code
│   └── evaluate.py
├── deployment/                 # Deployment scripts
│   ├── deploy_endpoint.py
│   └── wait_endpoint.py
├── tests/                      # Unit and integration tests
│   ├── test_preprocessing.py
│   ├── test_pipeline.py
│   └── test_endpoint.py
└── terraform/                  # Infrastructure as code
    └── main.tf
```

### ❌ DON'T: Monolithic Structure

```
project/
├── everything.py               # ❌ All code in one file
├── deploy.sh                   # ❌ Shell scripts everywhere
└── notebook.ipynb              # ❌ Production code in notebooks
```

## 2. GitHub Actions Workflows

### ✅ DO: Separate Workflows by Purpose

**model-build.yml** - Training only
```yaml
name: Model Build Pipeline
on:
  push:
    branches: [main, develop]
    paths:
      - 'pipelines/**'
      - 'preprocessing/**'
      - 'evaluation/**'
```

**model-deploy.yml** - Deployment only
```yaml
name: Model Deployment Pipeline
on:
  workflow_run:
    workflows: ["Model Build Pipeline"]
    types: [completed]
```

**code-quality.yml** - Testing and linting
```yaml
name: Code Quality
on:
  pull_request:
    branches: [main, develop]
```

### ❌ DON'T: One Massive Workflow

```yaml
# ❌ Don't put everything in one workflow
name: Everything
on: [push, pull_request, schedule, workflow_dispatch]
jobs:
  test-lint-train-deploy-monitor-everything: ...
```

## 3. SageMaker Pipeline Design

### ✅ DO: Parameterized Pipelines

```python
# Good: Parameterized and reusable
processing_instance_type = ParameterString(
    name="ProcessingInstanceType",
    default_value="ml.m5.xlarge"
)

training_instance_type = ParameterString(
    name="TrainingInstanceType",
    default_value="ml.m5.xlarge"
)

input_data = ParameterString(
    name="InputData",
    default_value=f"s3://{bucket}/data.csv"
)
```

### ❌ DON'T: Hardcoded Values

```python
# Bad: Hardcoded values
instance_type = "ml.m5.xlarge"  # ❌ Can't change without code update
bucket = "my-hardcoded-bucket"  # ❌ Not portable
```

### ✅ DO: Conditional Steps

```python
# Good: Conditional model registration
cond_gte = ConditionGreaterThanOrEqualTo(
    left=JsonGet(
        step_name=step_evaluate.name,
        property_file=evaluation_report,
        json_path="classification_metrics.accuracy.value"
    ),
    right=0.8  # Only register if accuracy >= 0.8
)

step_cond = ConditionStep(
    name="CheckAccuracy",
    conditions=[cond_gte],
    if_steps=[step_register],
    else_steps=[]
)
```

### ✅ DO: Proper Error Handling

```python
# Good: Retry logic for transient failures
step_train = TrainingStep(
    name="TrainModel",
    estimator=estimator,
    inputs=training_inputs,
    retry_policies=[
        StepRetryPolicy(
            exception_types=[
                StepExceptionTypeEnum.SERVICE_FAULT,
                StepExceptionTypeEnum.THROTTLING
            ],
            interval_seconds=60,
            backoff_rate=2.0,
            max_attempts=3
        )
    ]
)
```

## 4. Authentication & Security

### ✅ DO: Use OIDC (No Long-Lived Credentials)

```yaml
# Good: OIDC authentication
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: us-east-1
    role-session-name: GitHubActions-Build
```

**Terraform setup:**
```hcl
# OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# IAM Role with trust policy
resource "aws_iam_role" "github_actions" {
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
```

### ❌ DON'T: Store AWS Access Keys

```yaml
# ❌ Bad: Long-lived credentials
- name: Configure AWS
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### ✅ DO: Least Privilege IAM Policies

```hcl
# Good: Specific permissions only
resource "aws_iam_role_policy" "github_actions_build" {
  name = "GitHubActionsBuildPolicy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:CreatePipeline",
          "sagemaker:UpdatePipeline",
          "sagemaker:StartPipelineExecution",
          "sagemaker:DescribePipelineExecution"
        ]
        Resource = "arn:aws:sagemaker:*:*:pipeline/${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject"]
        Resource = "arn:aws:s3:::${var.bucket_name}/${var.project_name}/*"
      }
    ]
  })
}
```

### ❌ DON'T: Use Wildcard Permissions

```hcl
# ❌ Bad: Too broad
policy = jsonencode({
  Statement = [{
    Effect = "Allow"
    Action = "*"              # ❌ All actions
    Resource = "*"            # ❌ All resources
  }]
})
```

## 5. Environment Management

### ✅ DO: Use GitHub Environments

```yaml
# Good: Separate environments with protection rules
deploy-staging:
  environment:
    name: staging
    url: ${{ steps.deploy.outputs.endpoint_url }}
  # No approval required

deploy-production:
  environment:
    name: production
    url: ${{ steps.deploy.outputs.endpoint_url }}
  # Requires manual approval
```

**GitHub Settings:**
- Staging: No protection rules
- Production: Required reviewers, wait timer

### ✅ DO: Environment-Specific Configuration

```python
# Good: Environment-aware configuration
import os

ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

CONFIG = {
    'dev': {
        'instance_type': 'ml.t3.medium',
        'instance_count': 1,
        'enable_monitoring': False
    },
    'staging': {
        'instance_type': 'ml.m5.xlarge',
        'instance_count': 1,
        'enable_monitoring': True
    },
    'production': {
        'instance_type': 'ml.m5.xlarge',
        'instance_count': 2,
        'enable_monitoring': True,
        'enable_autoscaling': True
    }
}

config = CONFIG[ENVIRONMENT]
```

## 6. Testing Strategy

### ✅ DO: Multi-Level Testing

**Unit Tests** (Run in GitHub Actions)
```python
# tests/test_preprocessing.py
def test_data_split():
    """Test train/val/test split ratios."""
    from preprocessing.preprocess import split_data
    
    X, y = generate_sample_data(1000)
    train, val, test = split_data(X, y)
    
    assert len(train) == 700
    assert len(val) == 150
    assert len(test) == 150
```

**Integration Tests** (Run after deployment)
```python
# tests/test_endpoint.py
def test_endpoint_inference():
    """Test endpoint returns valid predictions."""
    import boto3
    
    runtime = boto3.client('sagemaker-runtime')
    response = runtime.invoke_endpoint(
        EndpointName='mlops-demo-staging',
        Body=test_data,
        ContentType='text/csv'
    )
    
    prediction = json.loads(response['Body'].read())
    assert 'predictions' in prediction
    assert 0 <= prediction['predictions'][0] <= 1
```

**Pipeline Tests** (Run before execution)
```python
# tests/test_pipeline.py
def test_pipeline_definition():
    """Test pipeline is valid."""
    from pipelines.create_pipeline import create_pipeline
    
    pipeline = create_pipeline(
        region='us-east-1',
        role='test-role',
        project_name='test'
    )
    
    assert pipeline.name == 'test-pipeline'
    assert len(pipeline.steps) >= 4
```

### ✅ DO: Test in CI Before Deployment

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pip install pytest
          pytest tests/ -v
      
  build:
    needs: test  # Only build if tests pass
    runs-on: ubuntu-latest
    steps:
      - name: Create pipeline
        run: python pipelines/create_pipeline.py
```

## 7. Monitoring & Observability

### ✅ DO: Comprehensive Logging

**GitHub Actions:**
```yaml
- name: Execute pipeline
  run: |
    echo "Starting pipeline execution..."
    python pipelines/run_pipeline.py \
      --pipeline-name ${{ env.PROJECT_NAME }}-pipeline \
      --region ${{ env.AWS_REGION }}
    
    echo "Pipeline execution started"
    echo "Execution ARN: $(cat execution_arn.txt)"
```

**SageMaker Pipeline:**
```python
# Enable detailed logging
pipeline = Pipeline(
    name=pipeline_name,
    steps=steps,
    sagemaker_session=sagemaker_session
)

# All steps automatically log to CloudWatch
```

### ✅ DO: Track Metrics

```yaml
- name: Get pipeline results
  run: |
    python pipelines/get_results.py \
      --execution-arn ${{ steps.execution.outputs.execution_arn }}
    
    # Extract metrics
    ACCURACY=$(jq -r '.accuracy' results.json)
    
    # Add to job summary
    cat >> $GITHUB_STEP_SUMMARY << EOF
    ## Model Metrics
    - Accuracy: $ACCURACY
    - Precision: $(jq -r '.precision' results.json)
    - Recall: $(jq -r '.recall' results.json)
    EOF
```

### ✅ DO: Set Up Alerts

**CloudWatch Alarms:**
```hcl
resource "aws_cloudwatch_metric_alarm" "endpoint_errors" {
  alarm_name          = "${var.project_name}-endpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocation5XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  
  dimensions = {
    EndpointName = "${var.project_name}-production"
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

## 8. Data Management

### ✅ DO: Version Your Data

```python
# Good: Versioned data paths
from datetime import datetime

data_version = datetime.now().strftime('%Y%m%d')
input_data = f"s3://{bucket}/{project}/data/v{data_version}/data.csv"

# Store version in pipeline parameters
input_data_param = ParameterString(
    name="InputData",
    default_value=input_data
)
```

### ✅ DO: Validate Data Quality

```python
# Add data quality check step
from sagemaker.processing import ProcessingInput, ProcessingOutput

step_data_quality = ProcessingStep(
    name="CheckDataQuality",
    processor=sklearn_processor,
    code="scripts/check_data_quality.py",
    inputs=[
        ProcessingInput(
            source=input_data,
            destination="/opt/ml/processing/input"
        )
    ],
    outputs=[
        ProcessingOutput(
            output_name="quality_report",
            source="/opt/ml/processing/output"
        )
    ]
)
```

## 9. Model Registry Best Practices

### ✅ DO: Use Model Registry

```python
# Good: Register models with metadata
step_register = RegisterModel(
    name="RegisterModel",
    estimator=estimator,
    model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["text/csv"],
    response_types=["application/json"],
    inference_instances=["ml.t2.medium", "ml.m5.xlarge"],
    transform_instances=["ml.m5.xlarge"],
    model_package_group_name=f"{project_name}-model-group",
    approval_status="PendingManualApproval",
    model_metrics=model_metrics,
    # Add custom metadata
    customer_metadata_properties={
        "training_date": datetime.now().isoformat(),
        "git_commit": os.getenv('GITHUB_SHA', 'unknown'),
        "trained_by": "github-actions"
    }
)
```

### ✅ DO: Implement Approval Workflow

```python
# scripts/approve_model.py
def approve_model_if_meets_criteria(model_package_arn, results):
    """Approve model if it meets quality criteria."""
    
    accuracy = results['accuracy']
    precision = results['precision']
    recall = results['recall']
    
    # Define approval criteria
    if (accuracy >= 0.85 and 
        precision >= 0.80 and 
        recall >= 0.80):
        
        sagemaker.update_model_package(
            ModelPackageArn=model_package_arn,
            ModelApprovalStatus='Approved'
        )
        print(f"✅ Model approved: {model_package_arn}")
        return True
    else:
        print(f"❌ Model does not meet criteria")
        return False
```

## 10. Deployment Strategies

### ✅ DO: Blue-Green Deployment

```python
# deployment/blue_green_deploy.py
def blue_green_deployment(endpoint_name, new_model_name):
    """Deploy new model with blue-green strategy."""
    
    # Get current endpoint config
    current_config = sagemaker.describe_endpoint(
        EndpointName=endpoint_name
    )['EndpointConfigName']
    
    # Create new endpoint config with both models
    new_config_name = f"{endpoint_name}-bg-{timestamp}"
    sagemaker.create_endpoint_config(
        EndpointConfigName=new_config_name,
        ProductionVariants=[
            {
                'VariantName': 'Blue',
                'ModelName': current_model_name,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.m5.xlarge',
                'InitialVariantWeight': 1.0  # 100% traffic
            },
            {
                'VariantName': 'Green',
                'ModelName': new_model_name,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.m5.xlarge',
                'InitialVariantWeight': 0.0  # 0% traffic initially
            }
        ]
    )
    
    # Update endpoint
    sagemaker.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=new_config_name
    )
    
    # Gradually shift traffic
    shift_traffic_gradually(endpoint_name, 'Green')
```

### ✅ DO: Canary Deployment

```python
# Start with 10% traffic to new model
sagemaker.update_endpoint_weights_and_capacities(
    EndpointName=endpoint_name,
    DesiredWeightsAndCapacities=[
        {
            'VariantName': 'Current',
            'DesiredWeight': 0.9
        },
        {
            'VariantName': 'Canary',
            'DesiredWeight': 0.1
        }
    ]
)

# Monitor metrics, then increase if successful
```

## 11. Cost Optimization

### ✅ DO: Use Spot Instances for Training

```python
# Good: Use spot instances for training
estimator = Estimator(
    image_uri=training_image,
    instance_type='ml.m5.xlarge',
    instance_count=1,
    use_spot_instances=True,  # Up to 90% cost savings
    max_wait=7200,  # Max wait time for spot
    max_run=3600,   # Max training time
    role=role
)
```

### ✅ DO: Right-Size Instances

```python
# Good: Start small, scale up if needed
INSTANCE_SIZES = {
    'small': 'ml.t3.medium',    # Development
    'medium': 'ml.m5.xlarge',   # Staging
    'large': 'ml.m5.2xlarge'    # Production
}

instance_type = INSTANCE_SIZES[environment]
```

### ✅ DO: Enable Autoscaling

```python
# Enable autoscaling for production
autoscaling = boto3.client('application-autoscaling')

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
        'TargetValue': 70.0,  # Target 70 invocations per instance
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        }
    }
)
```

## 12. Documentation

### ✅ DO: Document Everything

```
docs/
├── ARCHITECTURE.md          # System architecture
├── SETUP_GUIDE.md          # Setup instructions
├── DEPLOYMENT_GUIDE.md     # Deployment procedures
├── TROUBLESHOOTING.md      # Common issues
├── API_REFERENCE.md        # API documentation
└── RUNBOOK.md              # Operations runbook
```

### ✅ DO: Use Inline Documentation

```python
def create_pipeline(region: str, role: str, project_name: str) -> Pipeline:
    """
    Create SageMaker Pipeline for model training.
    
    Args:
        region: AWS region (e.g., 'us-east-1')
        role: SageMaker execution role ARN
        project_name: Project name for resource naming
        
    Returns:
        Pipeline: Configured SageMaker Pipeline
        
    Example:
        >>> pipeline = create_pipeline('us-east-1', role_arn, 'my-project')
        >>> pipeline.upsert(role_arn=role_arn)
    """
    # Implementation...
```

## 13. Common Anti-Patterns to Avoid

### ❌ DON'T: Train in GitHub Actions for Production

```yaml
# ❌ Bad: Training large models in GitHub Actions
- name: Train model
  run: |
    python train.py --epochs 100 --data large_dataset.csv
    # This will timeout and is not scalable
```

**Why:** GitHub Actions has 6-hour timeout, limited resources, no GPU support.

**Do Instead:** Use SageMaker Training Jobs or Pipelines.

### ❌ DON'T: Hardcode Secrets in Code

```python
# ❌ Bad: Hardcoded credentials
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**Do Instead:** Use GitHub Secrets and OIDC.

### ❌ DON'T: Skip Testing

```yaml
# ❌ Bad: Deploy without testing
- name: Deploy to production
  run: python deploy.py
  # No tests, no validation
```

**Do Instead:** Always test before deploying.

### ❌ DON'T: Use Single Environment

```yaml
# ❌ Bad: Deploy directly to production
- name: Deploy
  run: python deploy.py --env production
```

**Do Instead:** Use staging → production workflow.

## Summary: The Golden Rules

1. **Separate Concerns**: GitHub Actions for CI/CD, SageMaker for ML
2. **Use OIDC**: No long-lived credentials
3. **Test Everything**: Unit, integration, and pipeline tests
4. **Version Everything**: Code, data, models, infrastructure
5. **Monitor Everything**: Logs, metrics, alerts
6. **Automate Everything**: No manual steps in production
7. **Document Everything**: Code, architecture, procedures
8. **Secure Everything**: Least privilege, encryption, audit trails
9. **Cost Optimize**: Spot instances, right-sizing, autoscaling
10. **Fail Fast**: Validate early, fail early, recover quickly

## Quick Checklist

Before going to production, ensure:

- [ ] OIDC authentication configured
- [ ] Least privilege IAM policies
- [ ] Staging and production environments
- [ ] Manual approval for production
- [ ] Comprehensive testing (unit + integration)
- [ ] Monitoring and alerting set up
- [ ] Data versioning implemented
- [ ] Model registry in use
- [ ] Rollback procedure documented
- [ ] Cost optimization enabled
- [ ] Documentation complete
- [ ] Runbook created

## Resources

- [AWS SageMaker Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/best-practices.html)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [MLOps Best Practices](https://ml-ops.org/content/mlops-principles)
- [AWS Well-Architected Framework - ML Lens](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html)
