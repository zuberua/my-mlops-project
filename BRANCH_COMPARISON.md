# Branch Comparison

## Two Approaches to MLOps

This repository has two branches with different approaches:

### Main Branch: SageMaker Pipelines (Production-Grade)
**Best for:** Production workloads, large datasets, enterprise use

```
GitHub Actions → SageMaker Pipelines → SageMaker Endpoints
(Orchestration)   (Training on AWS)     (Serving)
```

**Training happens on:** AWS SageMaker (ml.m5.xlarge instances)

### github-actions-only Branch: GitHub Actions Only (Simplified)
**Best for:** Learning, prototyping, small datasets, cost optimization

```
GitHub Actions → GitHub Actions → SageMaker Endpoints
(Orchestration)   (Training on GitHub)  (Serving)
```

**Training happens on:** GitHub Actions runners (2-4 cores, 7-14GB RAM)

## Quick Comparison

| Feature | Main Branch | github-actions-only Branch |
|---------|-------------|----------------------------|
| **Training Location** | AWS SageMaker | GitHub Actions |
| **Scalability** | High (AWS resources) | Limited (GitHub runners) |
| **Cost (training)** | ~$0.07/run | $0/run (free tier) |
| **GPU Support** | ✅ Yes | ❌ No |
| **Max Training Time** | Unlimited | 6 hours |
| **Dataset Size** | Unlimited | < 1GB recommended |
| **Complexity** | Higher | Lower |
| **Setup Time** | 30 minutes | 10 minutes |
| **Best For** | Production | Learning/Prototyping |

## Detailed Comparison

### Architecture

#### Main Branch
```
Developer
    ↓ (git push)
GitHub Actions
    ↓ (creates pipeline)
SageMaker Pipeline
    ├─ PreprocessData (ml.m5.xlarge)
    ├─ TrainModel (ml.m5.xlarge)
    ├─ EvaluateModel (ml.m5.xlarge)
    └─ RegisterModel
        ↓
GitHub Actions
    ├─ Deploy Staging
    └─ Deploy Production
```

#### github-actions-only Branch
```
Developer
    ↓ (git push)
GitHub Actions
    ├─ Download data
    ├─ Preprocess (Python)
    ├─ Train (XGBoost)
    ├─ Evaluate (scikit-learn)
    ├─ Upload model
    ├─ Deploy Staging
    └─ Deploy Production
```

### Cost Breakdown

#### Main Branch (per month, 10 training runs)
- SageMaker Pipeline executions: $0.70
- Staging endpoint (24/7): $170
- Production endpoint (24/7): $340
- **Total: ~$511/month**

#### github-actions-only Branch (per month, 10 training runs)
- GitHub Actions: $0 (free tier)
- Staging endpoint (24/7): $170
- Production endpoint (24/7): $340
- **Total: ~$510/month**

**Savings: $0.70/month** (minimal, but training is free!)

### Use Cases

#### Main Branch - Use When:
✅ Production ML workloads
✅ Large datasets (> 1GB)
✅ Long training times (> 1 hour)
✅ Need GPU training
✅ Distributed training required
✅ Enterprise requirements
✅ Need SageMaker features (Experiments, Model Monitor, etc.)

#### github-actions-only Branch - Use When:
✅ Learning MLOps
✅ Small datasets (< 1GB)
✅ Simple models (XGBoost, scikit-learn)
✅ Quick prototyping
✅ Cost-sensitive projects
✅ Training time < 30 minutes
✅ No GPU needed

### Workflow Files

#### Main Branch
- `.github/workflows/model-build.yml` - Creates and runs SageMaker Pipeline
- `.github/workflows/model-deploy.yml` - Deploys to endpoints
- `pipelines/create_pipeline.py` - Defines SageMaker Pipeline
- `pipelines/run_pipeline.py` - Executes pipeline
- `pipelines/wait_pipeline.py` - Waits for completion

#### github-actions-only Branch
- `.github/workflows/train-and-deploy-simple.yml` - Everything in one file
- No separate pipeline scripts needed

### Complexity

#### Main Branch
**Pros:**
- Production-ready
- Scalable
- Robust error handling
- Better monitoring

**Cons:**
- More files to manage
- Steeper learning curve
- More AWS services involved

#### github-actions-only Branch
**Pros:**
- Simple to understand
- One workflow file
- Easy to debug
- Quick to set up

**Cons:**
- Limited scalability
- Less robust
- Not suitable for large ML

## How to Choose

### Choose Main Branch If:
- You're deploying to production
- You have datasets > 1GB
- You need GPU training
- You need distributed training
- You want enterprise features
- You're building for scale

### Choose github-actions-only Branch If:
- You're learning MLOps
- You have small datasets
- You want to minimize costs
- You need quick iterations
- You're prototyping
- You don't need GPUs

## Switching Between Branches

### Try github-actions-only First
```bash
# Clone repo
git clone https://github.com/zuberua/my-mlops-project.git
cd my-mlops-project

# Switch to simple branch
git checkout github-actions-only

# Follow GITHUB_ACTIONS_ONLY.md for setup
```

### Upgrade to Main Branch Later
```bash
# When you need more power
git checkout main

# Follow SETUP_GUIDE.md for setup
```

## Migration Path

### From github-actions-only → Main
When your project grows:
1. Switch to main branch
2. Your deployment code stays the same
3. Only training moves to SageMaker Pipelines
4. More scalable, more robust

### From Main → github-actions-only
If you want to simplify:
1. Switch to github-actions-only branch
2. Training moves to GitHub Actions
3. Deployment stays the same
4. Simpler, cheaper (for small projects)

## Recommendations

### For Learning
Start with **github-actions-only** branch:
- Simpler to understand
- Faster to set up
- Free training
- Learn core concepts

### For Production
Use **main** branch:
- Production-ready
- Scalable
- Robust
- Enterprise features

### For Prototyping
Use **github-actions-only** branch:
- Quick iterations
- Low cost
- Easy to experiment

### For Enterprise
Use **main** branch:
- Better monitoring
- Better security
- Better scalability
- Better integration

## Summary

Both branches deploy to the same SageMaker endpoints. The only difference is **where training happens**:

- **Main branch**: Training on AWS SageMaker (scalable, production-ready)
- **github-actions-only branch**: Training on GitHub Actions (simple, cheap)

Choose based on your needs:
- **Learning/Prototyping** → github-actions-only
- **Production/Scale** → main

You can always switch between them as your needs change!

## Resources

- [Main Branch Setup Guide](SETUP_GUIDE.md)
- [github-actions-only Branch Guide](GITHUB_ACTIONS_ONLY.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [SageMaker Pipelines Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html)
