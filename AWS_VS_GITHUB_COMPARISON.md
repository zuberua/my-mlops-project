# AWS Native vs GitHub Actions: Side-by-Side Comparison

## Lab 5: Deployment Pipeline Comparison

### AWS Native Approach (CodePipeline + CodeBuild)

```
┌─────────────────────────────────────────────────────────────┐
│  Model Registry (Model Approved)                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  EventBridge Rule                                           │
│  - Detects model approval                                   │
│  - Triggers CodePipeline                                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  CodePipeline: Deploy Pipeline                              │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Source                                            │
│  - CodeCommit repository                                    │
│  - Deployment scripts                                       │
│                                                              │
│  Stage 2: Build (CodeBuild)                                 │
│  - Generate CloudFormation templates                        │
│  - Package deployment artifacts                             │
│                                                              │
│  Stage 3: Deploy Staging (CloudFormation)                   │
│  - Create/update staging stack                              │
│  - Deploy endpoint                                          │
│                                                              │
│  Stage 4: Test Staging (CodeBuild)                          │
│  - Run automated tests                                      │
│  - Validate endpoint                                        │
│                                                              │
│  Stage 5: Manual Approval                                   │
│  - SNS notification                                         │
│  - Approve in CodePipeline console                          │
│                                                              │
│  Stage 6: Deploy Production (CloudFormation)                │
│  - Create/update production stack                           │
│  - Deploy endpoint                                          │
└─────────────────────────────────────────────────────────────┘
```

**Costs:**
- CodePipeline: $1/pipeline/month
- CodeBuild: $0.005/minute × build time
- CloudFormation: Free
- **Total:** ~$50-100/month

**Pros:**
- ✅ Native AWS integration
- ✅ Managed service
- ✅ Built-in approval mechanism

**Cons:**
- ❌ Multiple AWS consoles to manage
- ❌ Complex setup (CodeCommit, CodePipeline, CodeBuild, CloudFormation)
- ❌ Limited customization
- ❌ Costs for CodePipeline and CodeBuild
- ❌ Separate UI from code repository

---

### GitHub Actions Approach (This Solution)

```
┌─────────────────────────────────────────────────────────────┐
│  Model Registry (Model Approved)                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions: Model Deploy Workflow                      │
│  - Triggered by model build completion                      │
│  - Or manual trigger                                        │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Job 1: Deploy Staging                                      │
├─────────────────────────────────────────────────────────────┤
│  1. Checkout code                                           │
│  2. Setup Python                                            │
│  3. Configure AWS (OIDC - no keys!)                         │
│  4. Get latest approved model                               │
│  5. Deploy endpoint (Python script)                         │
│  6. Wait for InService                                      │
│  7. Run automated tests                                     │
│  8. Upload test results                                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  GitHub Environment: Production                             │
│  - Manual approval required                                 │
│  - Reviewers notified                                       │
│  - Approve in GitHub UI                                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Job 2: Deploy Production                                   │
├─────────────────────────────────────────────────────────────┤
│  1. Download staging test results                           │
│  2. Validate tests                                          │
│  3. Configure AWS (OIDC)                                    │
│  4. Get latest approved model                               │
│  5. Deploy endpoint with autoscaling                        │
│  6. Wait for InService                                      │
│  7. Run smoke tests                                         │
│  8. Enable Model Monitor                                    │
│  9. Send Slack notification                                 │
└─────────────────────────────────────────────────────────────┘
```

**Costs:**
- GitHub Actions: $0 (free tier: 2,000 min/month)
- **Total:** $0/month

**Pros:**
- ✅ Zero cost (free tier)
- ✅ Single UI (GitHub)
- ✅ Familiar to developers
- ✅ Easy to customize
- ✅ OIDC authentication (no AWS keys)
- ✅ Rich ecosystem (marketplace actions)
- ✅ Better visibility (inline with code)

**Cons:**
- ❌ Not native AWS (but uses AWS SDK)
- ❌ Requires GitHub account

---

## Feature Comparison

| Feature | AWS Native | GitHub Actions |
|---------|-----------|----------------|
| **Cost** | $50-100/month | $0/month |
| **Setup Complexity** | High (5 services) | Low (1 workflow file) |
| **UI** | Multiple AWS consoles | Single GitHub UI |
| **Authentication** | IAM keys/roles | OIDC (keyless) |
| **Approval Mechanism** | CodePipeline console | GitHub environments |
| **Customization** | Limited | Highly flexible |
| **Logs** | CloudWatch + CodeBuild | GitHub Actions UI |
| **Artifacts** | S3 | GitHub artifacts |
| **Notifications** | SNS | GitHub + Slack |
| **Version Control** | CodeCommit | GitHub |
| **PR Integration** | Limited | Native |
| **Marketplace** | None | 10,000+ actions |
| **Learning Curve** | Steep | Gentle |

---

## Code Comparison

### AWS Native: buildspec.yml (CodeBuild)

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.9
    commands:
      - pip install boto3 sagemaker
  
  build:
    commands:
      - echo "Deploying endpoint..."
      - python deploy_endpoint.py
      - echo "Testing endpoint..."
      - python test_endpoint.py
  
  post_build:
    commands:
      - echo "Deployment complete"

artifacts:
  files:
    - test_results.json
```

**Plus:**
- CloudFormation template (100+ lines)
- CodePipeline definition (JSON, 200+ lines)
- EventBridge rule
- IAM roles for CodePipeline, CodeBuild, CloudFormation

---

### GitHub Actions: model-deploy.yml

```yaml
name: Model Deployment Pipeline

on:
  workflow_run:
    workflows: ["Model Build Pipeline"]
    types: [completed]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy Endpoint
        run: python deployment/deploy_endpoint.py
      
      - name: Test Endpoint
        run: python tests/test_endpoint.py

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # Manual approval here!
    steps:
      - name: Deploy Production
        run: python deployment/deploy_endpoint.py
```

**That's it!** No CloudFormation, no CodePipeline JSON, no EventBridge rules.

---

## Approval Process Comparison

### AWS Native

1. Model approved in Model Registry
2. EventBridge triggers CodePipeline
3. Pipeline runs through stages
4. Reaches manual approval stage
5. SNS sends email notification
6. Approver logs into AWS Console
7. Navigates to CodePipeline
8. Finds the pipeline
9. Clicks "Review"
10. Clicks "Approve"

**Steps:** 10
**Time:** 2-3 minutes
**UI:** AWS Console

---

### GitHub Actions

1. Model approved in Model Registry
2. Workflow runs automatically
3. Staging deployment completes
4. GitHub sends notification
5. Approver clicks notification link
6. Clicks "Approve and deploy"

**Steps:** 6
**Time:** 30 seconds
**UI:** GitHub (familiar)

---

## Monitoring Comparison

### AWS Native

**Logs scattered across:**
- CloudWatch Logs (CodeBuild)
- CodePipeline execution history
- CloudFormation events
- SageMaker endpoint logs

**To debug:**
1. Check CodePipeline status
2. Click failed stage
3. Open CodeBuild logs
4. Search CloudWatch
5. Check CloudFormation events

---

### GitHub Actions

**All logs in one place:**
- GitHub Actions workflow run
- Expandable steps
- Real-time streaming
- Downloadable artifacts

**To debug:**
1. Click workflow run
2. Expand failed step
3. See error immediately

---

## Setup Time Comparison

### AWS Native Setup

**Time:** 2-4 hours

**Steps:**
1. Create CodeCommit repository
2. Create S3 bucket for artifacts
3. Create IAM roles (3-4 roles)
4. Create CodeBuild project
5. Create CloudFormation templates
6. Create CodePipeline
7. Configure EventBridge rule
8. Setup SNS for notifications
9. Test entire pipeline

**Files to create:** 10-15

---

### GitHub Actions Setup

**Time:** 30 minutes

**Steps:**
1. Create GitHub repository
2. Run `terraform apply` (creates IAM roles, S3, OIDC)
3. Add 2 secrets to GitHub
4. Create 2 environments
5. Push code

**Files to create:** 2 (workflow files)

---

## Real-World Scenario

### Scenario: Deploy a new model to production

#### AWS Native Approach

```
1. Approve model in Model Registry (AWS Console)
   ↓
2. Wait for EventBridge to trigger (1-2 min)
   ↓
3. CodePipeline starts (AWS Console)
   ↓
4. Source stage pulls from CodeCommit (1 min)
   ↓
5. Build stage runs CodeBuild (3-5 min)
   ↓
6. Deploy staging via CloudFormation (5-10 min)
   ↓
7. Test stage runs CodeBuild (2-3 min)
   ↓
8. Manual approval stage
   - Check email for SNS notification
   - Log into AWS Console
   - Navigate to CodePipeline
   - Review and approve (2-3 min)
   ↓
9. Deploy production via CloudFormation (5-10 min)
   ↓
10. Check CloudWatch for logs

Total time: 20-35 minutes
Consoles used: 4 (Model Registry, CodePipeline, CloudFormation, CloudWatch)
```

#### GitHub Actions Approach

```
1. Approve model in Model Registry (AWS Console)
   ↓
2. GitHub Actions triggers immediately
   ↓
3. Deploy staging (5-10 min)
   ↓
4. Test staging (2-3 min)
   ↓
5. Manual approval
   - Click GitHub notification
   - Review test results (inline)
   - Click "Approve and deploy" (30 sec)
   ↓
6. Deploy production (5-10 min)
   ↓
7. All logs in GitHub Actions UI

Total time: 15-25 minutes
Consoles used: 2 (Model Registry, GitHub)
```

**Time saved:** 5-10 minutes per deployment
**Complexity reduced:** 50%

---

## Migration Path

### From AWS Native to GitHub Actions

**Step 1:** Keep existing CodePipeline running

**Step 2:** Deploy GitHub Actions in parallel
```bash
cd sagemaker-mlops-github
terraform apply
# Configure GitHub
```

**Step 3:** Test GitHub Actions deployment
```bash
# Trigger manually first
gh workflow run model-deploy.yml
```

**Step 4:** Compare results
- Check both deployments work
- Verify endpoints are identical
- Compare logs and metrics

**Step 5:** Switch over
- Disable CodePipeline
- Use GitHub Actions as primary
- Keep CodePipeline as backup

**Step 6:** Decommission CodePipeline
```bash
# After 1-2 weeks of successful GitHub Actions
aws codepipeline delete-pipeline --name model-deploy-pipeline
```

---

## Conclusion

### Choose AWS Native If:
- ❌ Already heavily invested in CodePipeline
- ❌ Strict requirement to keep everything in AWS
- ❌ Team unfamiliar with GitHub

### Choose GitHub Actions If:
- ✅ Want to save costs
- ✅ Team already uses GitHub
- ✅ Want simpler setup and maintenance
- ✅ Need better developer experience
- ✅ Want more flexibility

**Recommendation:** For most teams, **GitHub Actions is the better choice** due to lower cost, simpler setup, and better developer experience while maintaining the same SageMaker functionality.
