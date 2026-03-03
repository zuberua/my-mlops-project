# Deployment Approach: Direct API vs CloudFormation

## Quick Answer

**No, we do NOT use CloudFormation templates** for deploying SageMaker endpoints.

We use **direct boto3 API calls** instead.

---

## Our Implementation (Direct API Calls)

### File: `deployment/deploy_endpoint.py`

```python
import boto3

sm_client = boto3.client("sagemaker")

# 1. Create Model
sm_client.create_model(
    ModelName=model_name,
    Containers=[{"ModelPackageName": model_package_arn}],
    ExecutionRoleArn=execution_role_arn
)

# 2. Create Endpoint Config
sm_client.create_endpoint_config(
    EndpointConfigName=endpoint_config_name,
    ProductionVariants=[{
        "VariantName": "AllTraffic",
        "ModelName": model_name,
        "InstanceType": "ml.m5.xlarge",
        "InitialInstanceCount": 1
    }]
)

# 3. Create Endpoint
sm_client.create_endpoint(
    EndpointName=endpoint_name,
    EndpointConfigName=endpoint_config_name
)

# 4. Configure Auto Scaling
autoscaling_client = boto3.client("application-autoscaling")
autoscaling_client.register_scalable_target(...)
autoscaling_client.put_scaling_policy(...)
```

**Approach:** Direct AWS SDK calls
**Language:** Python (boto3)
**Execution:** GitHub Actions runner

---

## AWS Workshop Lab 5 (CloudFormation)

### Original Approach

```yaml
# cloudformation/endpoint-template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'SageMaker Endpoint Deployment'

Parameters:
  ModelPackageArn:
    Type: String
  EndpointName:
    Type: String
  InstanceType:
    Type: String
    Default: ml.m5.xlarge

Resources:
  Model:
    Type: AWS::SageMaker::Model
    Properties:
      ModelName: !Sub '${EndpointName}-model'
      PrimaryContainer:
        ModelPackageName: !Ref ModelPackageArn
      ExecutionRoleArn: !GetAtt SageMakerRole.Arn

  EndpointConfig:
    Type: AWS::SageMaker::EndpointConfig
    Properties:
      EndpointConfigName: !Sub '${EndpointName}-config'
      ProductionVariants:
        - VariantName: AllTraffic
          ModelName: !GetAtt Model.ModelName
          InstanceType: !Ref InstanceType
          InitialInstanceCount: 1

  Endpoint:
    Type: AWS::SageMaker::Endpoint
    Properties:
      EndpointName: !Ref EndpointName
      EndpointConfigName: !GetAtt EndpointConfig.EndpointConfigName

Outputs:
  EndpointName:
    Value: !GetAtt Endpoint.EndpointName
```

**Approach:** Infrastructure as Code (CloudFormation)
**Language:** YAML/JSON
**Execution:** AWS CloudFormation service

---

## Detailed Comparison

### 1. Direct API Calls (Our Approach)

#### Pros:
✅ **Simpler** - No CloudFormation template needed
✅ **Faster** - Direct API calls, no stack creation overhead
✅ **More flexible** - Easy to add conditional logic
✅ **Better error handling** - Python try/except blocks
✅ **Easier debugging** - Direct Python code, clear error messages
✅ **No stack management** - No need to manage CloudFormation stacks
✅ **Easier updates** - Just update the endpoint, no stack updates
✅ **Less AWS services** - Only SageMaker, no CloudFormation

#### Cons:
❌ **No rollback** - Manual rollback if deployment fails
❌ **No drift detection** - Can't detect manual changes
❌ **Less declarative** - Imperative code vs declarative template
❌ **No stack outputs** - Need to manage outputs manually

#### Code Example:
```python
# deployment/deploy_endpoint.py
try:
    sm_client.describe_endpoint(EndpointName=endpoint_name)
    print("Endpoint exists, updating...")
    sm_client.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
except sm_client.exceptions.ClientError:
    print("Endpoint doesn't exist, creating...")
    sm_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name
    )
```

---

### 2. CloudFormation (AWS Workshop Approach)

#### Pros:
✅ **Declarative** - Describe desired state, AWS figures out how
✅ **Automatic rollback** - Rolls back on failure
✅ **Drift detection** - Detects manual changes
✅ **Stack management** - All resources in one stack
✅ **Change sets** - Preview changes before applying
✅ **Stack outputs** - Structured outputs
✅ **Better for complex infrastructure** - Multiple resources, dependencies

#### Cons:
❌ **More complex** - Need to write CloudFormation templates
❌ **Slower** - Stack creation/update overhead (~2-3 minutes)
❌ **Less flexible** - Limited conditional logic
❌ **Harder debugging** - CloudFormation error messages can be cryptic
❌ **Stack management overhead** - Need to manage stacks
❌ **More AWS services** - SageMaker + CloudFormation
❌ **Update limitations** - Some properties require replacement

#### Deployment Flow:
```
GitHub Actions
    ↓
AWS CodePipeline
    ↓
AWS CodeBuild (packages template)
    ↓
AWS CloudFormation (creates/updates stack)
    ↓
SageMaker Endpoint (created by CloudFormation)
```

---

## Why We Chose Direct API Calls

### 1. Simplicity
**CloudFormation:**
```
1. Write CloudFormation template (50-100 lines YAML)
2. Upload template to S3
3. Create/update stack via CloudFormation
4. Wait for stack to complete
5. Get outputs from stack
```

**Direct API:**
```
1. Write Python script (50-100 lines)
2. Run script
3. Done
```

---

### 2. Speed
**CloudFormation:**
- Stack creation: ~2-3 minutes
- Endpoint creation: ~8-10 minutes
- **Total: ~10-13 minutes**

**Direct API:**
- API calls: ~2 seconds
- Endpoint creation: ~8-10 minutes
- **Total: ~8-10 minutes**

**Savings: 2-3 minutes per deployment**

---

### 3. Flexibility
**CloudFormation:**
```yaml
# Hard to add conditional logic
Conditions:
  IsProduction: !Equals [!Ref Environment, 'production']

Resources:
  Endpoint:
    Type: AWS::SageMaker::Endpoint
    Properties:
      EndpointName: !Ref EndpointName
      # Can't easily add complex logic here
```

**Direct API:**
```python
# Easy to add conditional logic
if environment == 'production':
    instance_count = 2
    enable_autoscaling = True
    min_capacity = 2
    max_capacity = 10
else:
    instance_count = 1
    enable_autoscaling = False

sm_client.create_endpoint_config(
    ProductionVariants=[{
        "InitialInstanceCount": instance_count,
        # ... more logic
    }]
)

if enable_autoscaling:
    autoscaling_client.register_scalable_target(...)
```

---

### 4. Error Handling
**CloudFormation:**
```
Stack creation failed: Resource handler returned message: 
"Invalid request provided: CreateEndpointConfig request failed 
with status code 400 (Service: AmazonSageMaker; Status Code: 400; 
Error Code: ValidationException; Request ID: abc-123)"
```
- Cryptic error messages
- Need to check CloudFormation events
- Need to check SageMaker logs

**Direct API:**
```python
try:
    sm_client.create_endpoint(...)
except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceInUse':
        print("Endpoint already exists, updating instead...")
        sm_client.update_endpoint(...)
    elif e.response['Error']['Code'] == 'ValidationException':
        print(f"Validation error: {e.response['Error']['Message']}")
        raise
    else:
        print(f"Unexpected error: {e}")
        raise
```
- Clear error messages
- Easy to add custom error handling
- Direct Python debugging

---

### 5. No Stack Management
**CloudFormation:**
```bash
# List stacks
aws cloudformation list-stacks

# Describe stack
aws cloudformation describe-stacks --stack-name my-endpoint-stack

# Delete stack (deletes all resources)
aws cloudformation delete-stack --stack-name my-endpoint-stack

# Stack drift detection
aws cloudformation detect-stack-drift --stack-name my-endpoint-stack
```
- Need to manage stack lifecycle
- Stack can get into bad state
- Need to handle stack updates vs replacements

**Direct API:**
```bash
# List endpoints
aws sagemaker list-endpoints

# Describe endpoint
aws sagemaker describe-endpoint --endpoint-name my-endpoint

# Delete endpoint
aws sagemaker delete-endpoint --endpoint-name my-endpoint
```
- Direct resource management
- No stack state to worry about
- Simpler operations

---

## When to Use Each Approach

### Use Direct API Calls When:
✅ Simple deployments (1-3 resources)
✅ Need flexibility and custom logic
✅ Want faster deployments
✅ Prefer Python over YAML
✅ Don't need automatic rollback
✅ Want simpler debugging

**Example:** Our MLOps project
- Deploy SageMaker endpoints
- Configure auto scaling
- Simple, fast, flexible

---

### Use CloudFormation When:
✅ Complex infrastructure (10+ resources)
✅ Need automatic rollback
✅ Want drift detection
✅ Managing multiple related resources
✅ Need change sets for review
✅ Want declarative infrastructure

**Example:** Full AWS infrastructure
- VPC, subnets, security groups
- Multiple SageMaker resources
- Lambda functions, API Gateway
- DynamoDB tables, S3 buckets
- IAM roles and policies

---

## Hybrid Approach (Best of Both Worlds)

You can use **both** approaches:

### Infrastructure: Terraform/CloudFormation
```hcl
# terraform/main.tf
resource "aws_s3_bucket" "sagemaker_bucket" { ... }
resource "aws_iam_role" "sagemaker_execution_role" { ... }
resource "aws_iam_role" "github_actions_role" { ... }
resource "aws_sagemaker_model_package_group" "model_group" { ... }
```
**Use for:** Long-lived infrastructure that rarely changes

### Deployments: Direct API Calls
```python
# deployment/deploy_endpoint.py
sm_client.create_endpoint(...)
```
**Use for:** Frequent deployments that change often

**This is what we do!**
- Terraform for infrastructure (IAM, S3, Model Registry)
- Python scripts for deployments (Endpoints)

---

## Cost Comparison

### CloudFormation Approach (AWS Workshop)
```
AWS CodePipeline: $1/month per pipeline
AWS CodeBuild: $0.005/minute
CloudFormation: Free
SageMaker Endpoints: $170-1700/month

Total: ~$171-1701/month
```

### Direct API Approach (Our Implementation)
```
GitHub Actions: Free (within limits)
CloudFormation: Not used
SageMaker Endpoints: $170-1700/month

Total: ~$170-1700/month
```

**Savings: ~$1/month** (minimal, but simpler)

---

## Migration Path

### From CloudFormation to Direct API

If you have existing CloudFormation stacks:

1. **Export resources:**
```bash
aws cloudformation describe-stack-resources \
  --stack-name my-endpoint-stack
```

2. **Import to Python:**
```python
# Get existing endpoint
response = sm_client.describe_endpoint(
    EndpointName='my-endpoint'
)

# Update with new config
sm_client.update_endpoint(
    EndpointName='my-endpoint',
    EndpointConfigName='new-config'
)
```

3. **Delete stack (optional):**
```bash
# Delete stack but retain resources
aws cloudformation delete-stack \
  --stack-name my-endpoint-stack \
  --retain-resources Endpoint
```

---

### From Direct API to CloudFormation

If you want to move to CloudFormation:

1. **Create template:**
```yaml
# Import existing resources
Resources:
  Endpoint:
    Type: AWS::SageMaker::Endpoint
    Properties:
      EndpointName: my-endpoint
      # ... other properties
```

2. **Import stack:**
```bash
aws cloudformation create-stack \
  --stack-name my-endpoint-stack \
  --template-body file://template.yaml \
  --resources-to-import file://resources.json
```

---

## Summary

### Our Implementation
- ✅ **No CloudFormation** for endpoint deployment
- ✅ **Direct boto3 API calls** in Python
- ✅ **Simpler, faster, more flexible**
- ✅ **Terraform for infrastructure** (IAM, S3, etc.)
- ✅ **Python for deployments** (endpoints)

### AWS Workshop Lab 5
- Uses **CloudFormation** for endpoint deployment
- Uses **CodePipeline + CodeBuild** for orchestration
- More complex, slower, but more declarative

### Why We're Different
- **Simpler:** No CloudFormation templates needed
- **Faster:** Direct API calls, no stack overhead
- **Cheaper:** No CodePipeline/CodeBuild costs
- **Flexible:** Easy to add custom logic in Python

---

## File Structure Comparison

### Our Implementation
```
my-mlops-project/
├── .github/workflows/
│   └── model-deploy.yml          # GitHub Actions workflow
├── deployment/
│   ├── deploy_endpoint.py        # Direct API calls
│   └── wait_endpoint.py          # Polling script
├── terraform/
│   └── main.tf                   # Infrastructure only
└── scripts/
    └── get_latest_model.py       # Helper scripts
```

### AWS Workshop Lab 5
```
mlops-project/
├── cloudformation/
│   ├── endpoint-template.yaml    # CloudFormation template
│   └── parameters.json           # Template parameters
├── codepipeline/
│   └── pipeline-definition.json  # CodePipeline config
└── codebuild/
    └── buildspec.yml             # CodeBuild config
```

---

## Related Documentation

- [LAB5_WHAT_RUNS_IN_GITHUB_ACTIONS.md](LAB5_WHAT_RUNS_IN_GITHUB_ACTIONS.md) - What runs where
- [GITHUB_AWS_AUTHENTICATION.md](GITHUB_AWS_AUTHENTICATION.md) - Authentication details
- [IMPLEMENTATION_COMPARISON.md](IMPLEMENTATION_COMPARISON.md) - Full comparison with AWS Workshop
