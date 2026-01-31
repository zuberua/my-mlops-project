# SageMaker MLOps with GitHub Actions - Project Summary

## What This Project Does

This is a **complete MLOps solution** that replaces AWS CodePipeline and CodeBuild with **GitHub Actions** for CI/CD, while still using Amazon SageMaker for ML infrastructure.

## Key Differences from AWS Native Solution

| Component | AWS Native | This Solution |
|-----------|-----------|---------------|
| **CI/CD** | CodePipeline + CodeBuild | GitHub Actions |
| **Source Control** | CodeCommit | GitHub |
| **Authentication** | IAM Users/Keys | OIDC (keyless) |
| **ML Infrastructure** | SageMaker | SageMaker (same) |
| **Cost** | Pay for CodePipeline + CodeBuild | Free (GitHub Actions) |
| **UI** | AWS Console | GitHub UI |
| **Approval Gates** | Manual approval in CodePipeline | GitHub Environments |

## Architecture Overview

```
Developer → GitHub → GitHub Actions → AWS SageMaker
                ↓
            OIDC Auth (no keys!)
                ↓
        ┌───────────────────┐
        │  Model Build      │
        │  - Test code      │
        │  - Train model    │
        │  - Evaluate       │
        │  - Register       │
        └───────────────────┘
                ↓
        ┌───────────────────┐
        │  Model Deploy     │
        │  - Deploy staging │
        │  - Test endpoint  │
        │  - Manual approve │
        │  - Deploy prod    │
        └───────────────────┘
```

## What Gets Created

### AWS Resources (via Terraform)
1. **S3 Bucket** - Stores models, data, artifacts
2. **IAM Roles** - SageMaker execution, GitHub Actions
3. **Model Package Group** - Version control for models
4. **OIDC Provider** - Secure GitHub authentication
5. **SageMaker Pipeline** - ML workflow (created by GitHub Actions)
6. **SageMaker Endpoints** - Staging and production (created by GitHub Actions)

### GitHub Resources (manual setup)
1. **Repository Secrets** - AWS role ARNs
2. **Environments** - Staging (auto) and Production (manual approval)
3. **Workflows** - Model build and deploy automation

## Complete Workflow

### 1. Developer Makes Changes
```bash
git add preprocessing/preprocess.py
git commit -m "Improve feature engineering"
git push origin main
```

### 2. GitHub Actions: Model Build
- ✅ Runs tests
- ✅ Creates SageMaker Pipeline
- ✅ Trains model
- ✅ Evaluates model
- ✅ Registers model (if accuracy >= 0.8)
- ✅ Auto-approves model (if accuracy >= 0.8)

### 3. GitHub Actions: Deploy Staging
- ✅ Gets latest approved model
- ✅ Deploys to staging endpoint
- ✅ Runs automated tests
- ✅ Uploads test results

### 4. Manual Approval
- 🔒 GitHub environment protection
- 👤 Reviewer checks staging results
- ✅ Approves production deployment

### 5. GitHub Actions: Deploy Production
- ✅ Validates staging tests
- ✅ Deploys to production endpoint (with autoscaling)
- ✅ Runs smoke tests
- ✅ Enables Model Monitor
- 📢 Sends Slack notification

## Files Structure

```
sagemaker-mlops-github/
├── .github/workflows/          # GitHub Actions workflows
│   ├── model-build.yml         # Build and train
│   └── model-deploy.yml        # Deploy to staging/prod
├── pipelines/                  # SageMaker Pipeline code
│   ├── create_pipeline.py      # Define ML workflow
│   ├── run_pipeline.py         # Start execution
│   ├── wait_pipeline.py        # Wait for completion
│   └── get_results.py          # Extract metrics
├── preprocessing/              # Data preprocessing
│   └── preprocess.py
├── evaluation/                 # Model evaluation
│   └── evaluate.py
├── deployment/                 # Endpoint deployment
│   ├── deploy_endpoint.py
│   └── wait_endpoint.py
├── scripts/                    # Helper scripts
│   ├── get_latest_model.py
│   ├── approve_model.py
│   └── validate_tests.py
├── tests/                      # Testing
│   ├── test_endpoint.py
│   └── test_data.json
├── monitoring/                 # Model monitoring
│   └── setup_monitor.py
├── terraform/                  # Infrastructure as code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── README.md                   # Main documentation
├── SETUP_GUIDE.md             # Step-by-step setup
├── QUICK_REFERENCE.md         # Command reference
└── requirements.txt           # Python dependencies
```

## Benefits

### 1. Cost Savings
- **No CodePipeline costs** (~$1/pipeline/month)
- **No CodeBuild costs** (~$0.005/build minute)
- **Free GitHub Actions** (2,000 minutes/month for free accounts)

### 2. Better Developer Experience
- ✅ Familiar GitHub UI
- ✅ Pull request integration
- ✅ Inline comments on code
- ✅ Rich workflow visualization
- ✅ Artifact downloads

### 3. Enhanced Security
- ✅ OIDC authentication (no long-lived keys)
- ✅ Least privilege IAM roles
- ✅ Environment protection rules
- ✅ Audit trail in GitHub

### 4. Flexibility
- ✅ Easy to customize workflows
- ✅ Reusable actions from marketplace
- ✅ Matrix builds for multiple configurations
- ✅ Conditional execution

### 5. Collaboration
- ✅ Code reviews on PRs
- ✅ Team approvals
- ✅ Inline discussions
- ✅ Notifications

## Comparison: Before vs After

### Before (AWS Native)
```
CodeCommit → CodePipeline → CodeBuild → SageMaker
    ↓            ↓              ↓
  Limited    Complex UI    Separate logs
   UI        Multiple      Multiple
            consoles       consoles
```

### After (GitHub Actions)
```
GitHub → GitHub Actions → SageMaker
   ↓           ↓
Familiar   Single UI
   UI      All logs
          in one place
```

## Use Cases

### Perfect For:
- ✅ Teams already using GitHub
- ✅ Open source ML projects
- ✅ Startups wanting to minimize costs
- ✅ Projects needing PR-based workflows
- ✅ Multi-cloud strategies

### Consider AWS Native If:
- ❌ Already heavily invested in AWS CodePipeline
- ❌ Strict requirement to keep everything in AWS
- ❌ Need AWS-specific integrations (e.g., CodeGuru)

## Getting Started

### Quick Start (5 minutes)
```bash
# 1. Clone repo
git clone <your-repo>

# 2. Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init && terraform apply

# 3. Configure GitHub secrets
# Add AWS_ROLE_ARN and SAGEMAKER_EXECUTION_ROLE_ARN

# 4. Create GitHub environments
# staging (no protection)
# production (require approval)

# 5. Push code
git push origin main
```

### Full Setup (30 minutes)
See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

## Customization Points

### Easy to Change:
- ✅ ML algorithm (XGBoost → PyTorch/TensorFlow)
- ✅ Instance types
- ✅ Approval thresholds
- ✅ Test cases
- ✅ Deployment strategy

### Requires Code Changes:
- Data preprocessing logic
- Feature engineering
- Model evaluation metrics
- Custom monitoring

## Monitoring & Observability

### GitHub Actions
- Workflow runs history
- Step-by-step logs
- Artifact downloads
- Email notifications

### AWS CloudWatch
- SageMaker metrics
- Endpoint latency
- Invocation counts
- Model Monitor results

### Slack Integration
- Deployment notifications
- Failure alerts
- Custom messages

## Cost Breakdown

### Monthly Costs (Typical)
- **GitHub Actions:** $0 (free tier)
- **SageMaker Training:** $10-50 (on-demand)
- **Staging Endpoint:** $170 (24/7)
- **Production Endpoint:** $340-1,700 (2-10 instances)
- **S3 Storage:** $5-10
- **Data Transfer:** $5-10
- **Total:** $530-1,940/month

### Cost Optimization
- Use Spot instances for training (-70%)
- Stop staging when not needed
- Use Serverless Inference
- Enable SageMaker Savings Plans (-64%)

## Success Metrics

After setup, you should have:
- ✅ Automated model training on every push
- ✅ Automatic model registration
- ✅ Staging deployment with tests
- ✅ Manual approval gate for production
- ✅ Production deployment with monitoring
- ✅ Complete audit trail
- ✅ Zero long-lived AWS credentials

## Next Steps

1. **Customize for your data** - Update preprocessing/training/evaluation
2. **Add more tests** - Expand test coverage
3. **Setup alerts** - CloudWatch alarms for failures
4. **Add A/B testing** - Deploy multiple model variants
5. **Implement retraining** - Automate model updates
6. **Add Feature Store** - Centralize feature management

## Support & Resources

- 📖 [Full Documentation](README.md)
- 🚀 [Setup Guide](SETUP_GUIDE.md)
- ⚡ [Quick Reference](QUICK_REFERENCE.md)
- 🔗 [AWS SageMaker Docs](https://docs.aws.amazon.com/sagemaker/)
- 🔗 [GitHub Actions Docs](https://docs.github.com/en/actions)

## License

MIT License - Free to use and modify!

---

**Ready to get started?** Follow the [SETUP_GUIDE.md](SETUP_GUIDE.md) for step-by-step instructions!
