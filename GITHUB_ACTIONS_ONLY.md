# GitHub Actions Only Branch

This branch runs **everything in GitHub Actions** without using SageMaker Pipelines.

## Key Differences from Main Branch

| Aspect | Main Branch | This Branch (github-actions-only) |
|--------|-------------|-----------------------------------|
| **Training Location** | SageMaker Pipeline (AWS) | GitHub Actions (GitHub servers) |
| **Orchestration** | SageMaker Pipelines | GitHub Actions workflows |
| **Data Processing** | SageMaker Processing Jobs | Python scripts in GitHub Actions |
| **Model Training** | SageMaker Training Jobs | XGBoost training in GitHub Actions |
| **Evaluation** | SageMaker Processing Jobs | Python scripts in GitHub Actions |
| **Deployment** | Same (SageMaker Endpoints) | Same (SageMaker Endpoints) |
| **Cost** | Higher (SageMaker compute) | Lower (GitHub Actions free tier) |
| **Scalability** | High (AWS resources) | Limited (GitHub runners) |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    GitHub Actions                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  1. Download data from S3                          │  │
│  │  2. Preprocess data (Python)                       │  │
│  │  3. Train model (XGBoost)                          │  │
│  │  4. Evaluate model (scikit-learn)                  │  │
│  │  5. Upload model to S3                             │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│              Deploy to SageMaker Endpoints                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Staging: ml.m5.xlarge (1 instance)                │  │
│  │  Production: ml.m5.xlarge (2 instances)            │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Workflow

### Single Workflow File
- `.github/workflows/train-and-deploy-simple.yml`

### Three Jobs

#### 1. Train Model (runs on GitHub Actions)
- Downloads data from S3
- Preprocesses data (train/val/test split)
- Trains XGBoost model
- Evaluates model
- Uploads model to S3 if accuracy >= 0.8

#### 2. Deploy Staging (runs if training succeeds)
- Creates SageMaker model
- Deploys to staging endpoint
- Tests endpoint

#### 3. Deploy Production (requires manual approval)
- Creates SageMaker model
- Deploys to production endpoint
- 2 instances for high availability

## Advantages

### ✅ Simpler
- One workflow file instead of multiple
- No SageMaker Pipeline complexity
- Easier to understand and debug

### ✅ Cheaper
- GitHub Actions free tier: 2,000 minutes/month
- No SageMaker Processing/Training job costs
- Only pay for endpoints

### ✅ Faster Iteration
- No pipeline creation/update step
- Direct execution
- Faster feedback loop

### ✅ More Control
- Full control over execution environment
- Easy to add custom logic
- Flexible workflow structure

## Disadvantages

### ❌ Limited Scalability
- GitHub runners: 2-4 cores, 7-14GB RAM
- 6-hour timeout per job
- Not suitable for large datasets or long training

### ❌ No GPU Support
- GitHub Actions runners don't have GPUs
- Can't train deep learning models efficiently

### ❌ Less Robust
- No built-in retry logic
- No distributed training
- No automatic resource management

### ❌ Not Production-Grade for Large ML
- SageMaker Pipelines designed for production ML
- Better monitoring and logging
- Better integration with AWS ML services

## When to Use This Branch

### ✅ Good For:
- **Small to medium datasets** (< 1GB)
- **Simple models** (XGBoost, scikit-learn)
- **Quick prototyping**
- **Cost-sensitive projects**
- **Learning and experimentation**
- **Startups with limited budget**

### ❌ Not Good For:
- **Large datasets** (> 1GB)
- **Deep learning models** (need GPUs)
- **Long training times** (> 1 hour)
- **Distributed training**
- **Production-scale ML**
- **Enterprise requirements**

## Setup

### 1. Switch to Branch
```bash
git checkout github-actions-only
```

### 2. Push to GitHub
```bash
git push origin github-actions-only
```

### 3. Configure GitHub Secrets
Same as main branch:
- `AWS_ROLE_ARN`
- `SAGEMAKER_EXECUTION_ROLE_ARN`

### 4. Create GitHub Environments
- `staging` (no protection)
- `production` (require approval)

### 5. Trigger Workflow
```bash
# Push changes
git add .
git commit -m "Update training code"
git push origin github-actions-only

# Or trigger manually
gh workflow run train-and-deploy-simple.yml
```

## Monitoring

### GitHub Actions
- Go to Actions tab
- Click on workflow run
- View logs for each step

### SageMaker Endpoints
- AWS Console → SageMaker → Endpoints
- Check endpoint status
- View CloudWatch metrics

## Cost Comparison

### Main Branch (SageMaker Pipelines)
**Per Training Run:**
- Processing (preprocess): ml.m5.xlarge × 5 min = $0.02
- Training: ml.m5.xlarge × 10 min = $0.04
- Processing (evaluate): ml.m5.xlarge × 3 min = $0.01
- **Total per run:** ~$0.07

**Monthly (10 runs):**
- Training: $0.70
- Staging endpoint: $170 (24/7)
- Production endpoint: $340 (24/7)
- **Total:** ~$511/month

### This Branch (GitHub Actions Only)
**Per Training Run:**
- GitHub Actions: $0 (free tier)
- **Total per run:** $0

**Monthly (10 runs):**
- Training: $0
- Staging endpoint: $170 (24/7)
- Production endpoint: $340 (24/7)
- **Total:** ~$510/month

**Savings:** ~$0.70/month on training (minimal, but free is free!)

## Customization

### Change Training Algorithm
Edit the "Train model" step in the workflow:

```python
# Instead of XGBoost
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)
```

### Add More Preprocessing
Edit the "Preprocess data" step:

```python
# Add feature engineering
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

### Change Evaluation Metrics
Edit the "Evaluate model" step:

```python
# Add more metrics
from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_test, y_pred)
print(f'Confusion Matrix:\n{cm}')
```

## Troubleshooting

### Training Fails
- Check GitHub Actions logs
- Verify data is in S3
- Check Python dependencies

### Deployment Fails
- Verify AWS credentials
- Check SageMaker execution role
- Ensure model uploaded to S3

### Timeout Issues
- Reduce dataset size
- Simplify model
- Use SageMaker Pipelines instead

## Migration Path

### From This Branch to Main Branch
If your project grows and needs SageMaker Pipelines:

```bash
# Merge changes back to main
git checkout main
git merge github-actions-only

# Use main branch workflows
# They use SageMaker Pipelines for scalability
```

### From Main Branch to This Branch
If you want to simplify:

```bash
# Switch to this branch
git checkout github-actions-only

# Cherry-pick specific changes
git cherry-pick <commit-hash>
```

## Best Practices

### ✅ DO:
- Use for small datasets and simple models
- Monitor GitHub Actions usage (free tier limits)
- Test locally before pushing
- Keep training time under 30 minutes
- Use caching for dependencies

### ❌ DON'T:
- Train large models (use SageMaker instead)
- Process huge datasets (use SageMaker instead)
- Rely on this for production-scale ML
- Exceed GitHub Actions timeout (6 hours)
- Store sensitive data in workflow files

## Comparison Summary

This branch is **simpler and cheaper** but **less scalable** than the main branch.

**Use this branch if:**
- You're learning MLOps
- You have small datasets
- You want to minimize costs
- You need quick iterations

**Use main branch if:**
- You have production workloads
- You need scalability
- You have large datasets
- You need enterprise features

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [SageMaker Endpoints](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)

## Questions?

See the main README.md for general setup instructions. This branch only changes where training happens (GitHub Actions vs SageMaker Pipelines).
