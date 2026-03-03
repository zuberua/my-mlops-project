# How Deployment Gets Triggered After Model Approval

## Quick Answer

The deployment workflow is triggered **automatically when the build workflow completes**, NOT when the model is approved in Model Registry.

---

## The Complete Flow

### Step 1: Training Pipeline Completes
```
Model Build Workflow runs
    ↓
Model is registered with "PendingManualApproval" status
    ↓
Model is automatically approved (if accuracy >= 0.8)
    ↓
Build workflow completes successfully
```

### Step 2: Deployment Workflow Triggers
```
Build workflow completes
    ↓
GitHub detects completion
    ↓
Deployment workflow AUTOMATICALLY starts
```

---

## Trigger Configuration

### File: `.github/workflows/model-deploy.yml`

```yaml
on:
  workflow_run:
    workflows: ["Model Build Pipeline"]  # Watch this workflow
    types:
      - completed                        # Trigger when it completes
    branches:
      - main                             # Only on main branch
```

**What this means:**
- Deployment workflow watches the "Model Build Pipeline" workflow
- When build workflow completes (success or failure), deployment triggers
- Only triggers for main branch

---

## Three Ways Deployment Can Be Triggered

### 1. Automatic (After Build Completes) ⭐ PRIMARY METHOD

```yaml
on:
  workflow_run:
    workflows: ["Model Build Pipeline"]
    types:
      - completed
```

**When:** Build workflow finishes
**Condition:** Checks if build was successful
**Frequency:** Every time build completes on main branch

---

### 2. Manual Dispatch (Manual Trigger)

```yaml
on:
  workflow_dispatch:
    inputs:
      model_package_arn:
        description: 'Model Package ARN to deploy'
        required: true
```

**When:** You manually click "Run workflow" in GitHub UI
**Use case:** Deploy a specific model version
**How:** 
1. Go to Actions tab
2. Select "Model Deployment Pipeline"
3. Click "Run workflow"
4. Enter model package ARN

---

### 3. Repository Dispatch (API Trigger)

```yaml
on:
  repository_dispatch:
    types: [model-approved]
```

**When:** External system sends API call to GitHub
**Use case:** Trigger from external automation
**How:**
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/dispatches \
  -d '{"event_type":"model-approved"}'
```

---

## Detailed Timeline

### What Actually Happens:

```
Time: 0:00 - Developer pushes code to main branch
    ↓
Time: 0:01 - Build workflow starts
    ↓
Time: 0:02 - Build workflow creates/updates SageMaker Pipeline
    ↓
Time: 0:03 - Build workflow starts pipeline execution
    ↓
Time: 0:03-0:40 - SageMaker Pipeline runs (preprocess, train, evaluate)
    ↓
Time: 0:40 - Model registered with "PendingManualApproval"
    ↓
Time: 0:41 - approve_model.py checks accuracy
    ↓
Time: 0:41 - If accuracy >= 0.8, model status → "Approved"
    ↓
Time: 0:42 - Build workflow completes ✓
    ↓
Time: 0:42 - GitHub detects build completion
    ↓
Time: 0:42 - Deployment workflow AUTOMATICALLY triggers
    ↓
Time: 0:43 - Deployment workflow starts staging deployment
```

---

## Key Points

### Model Approval Happens DURING Build Workflow

**File:** `.github/workflows/model-build.yml`

```yaml
jobs:
  build-and-train:
    # ... training steps ...
  
  register-model:
    needs: build-and-train
    steps:
      - name: Approve Model for Deployment
        run: |
          python scripts/approve_model.py \
            --results-file results.json \
            --region us-east-1
```

**What happens:**
1. Training completes
2. Model registered as "PendingManualApproval"
3. `approve_model.py` runs
4. If accuracy >= 0.8, model status → "Approved"
5. Build workflow completes

---

### Deployment Triggers AFTER Build Completes

**File:** `.github/workflows/model-deploy.yml`

```yaml
jobs:
  deploy-staging:
    # Only run if build was successful
    if: github.event.workflow_run.conclusion == 'success'
    
    steps:
      - name: Get Latest Approved Model
        run: |
          python scripts/get_latest_model.py \
            --status Approved
```

**What happens:**
1. Deployment workflow starts
2. Checks if build was successful
3. Gets latest approved model from Model Registry
4. Deploys to staging

---

## Why This Design?

### Automatic Deployment After Successful Build

✅ **Fast feedback** - No manual intervention needed
✅ **Consistent** - Always deploys after successful build
✅ **Traceable** - Clear link between build and deployment
✅ **Automated** - Fully automated CI/CD pipeline

### Manual Approval for Production

✅ **Safety gate** - Human reviews before production
✅ **Flexibility** - Can reject if needed
✅ **Compliance** - Meets audit requirements

---

## Comparison with AWS Workshop

### AWS Workshop (CodePipeline)

```
CodeCommit push
    ↓
EventBridge rule triggers
    ↓
CodePipeline starts
    ↓
CodeBuild runs training
    ↓
Model approved in Model Registry
    ↓
CodePipeline continues (manual approval)
    ↓
CloudFormation deploys endpoint
```

**Trigger:** EventBridge rule on CodeCommit push

---

### Our Implementation (GitHub Actions)

```
GitHub push
    ↓
Build workflow starts (automatic)
    ↓
SageMaker Pipeline runs training
    ↓
Model approved in Model Registry
    ↓
Build workflow completes
    ↓
Deployment workflow starts (automatic)
    ↓
Staging deploys (automatic)
    ↓
Production deploys (manual approval)
```

**Trigger:** `workflow_run` on build completion

---

## Visual Flow

```
┌─────────────────────────────────────────────────────────┐
│  Developer pushes code to main                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Build Workflow (model-build.yml)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Create SageMaker Pipeline                    │   │
│  │ 2. Execute Pipeline (train model)               │   │
│  │ 3. Register model (PendingManualApproval)       │   │
│  │ 4. Approve model (if accuracy >= 0.8)           │   │
│  │ 5. Workflow completes ✓                         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓
                  [workflow_run trigger]
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Deployment Workflow (model-deploy.yml)                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Get latest approved model                    │   │
│  │ 2. Deploy to staging (automatic)                │   │
│  │ 3. Test staging                                 │   │
│  │ 4. Wait for manual approval ⏸                   │   │
│  │ 5. Deploy to production (after approval)        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Common Misconceptions

### ❌ WRONG: Model approval triggers deployment
**Reality:** Build workflow completion triggers deployment

### ❌ WRONG: Manual approval in Model Registry
**Reality:** Model approval is automatic (if accuracy >= 0.8)

### ❌ WRONG: Manual approval triggers deployment
**Reality:** Manual approval is for production deployment, not triggering workflow

### ✅ CORRECT: Build completion triggers deployment
**Reality:** `workflow_run` trigger starts deployment automatically

---

## How to Verify

### Check Workflow Runs

1. Go to GitHub Actions tab
2. Look at workflow runs
3. You'll see:
   - "Model Build Pipeline" completes
   - "Model Deployment Pipeline" starts immediately after

### Check Workflow Logs

**Build workflow (last step):**
```
✓ Approve Model for Deployment
  Model approved: arn:aws:sagemaker:...
  Workflow completed successfully
```

**Deployment workflow (first step):**
```
Triggered by workflow_run: Model Build Pipeline
Build workflow conclusion: success
Starting deployment...
```

---

## Summary

**Question:** How does deployment get triggered after model approval?

**Answer:** 
1. Model is approved **during** the build workflow (automatic if accuracy >= 0.8)
2. Build workflow completes
3. Deployment workflow **automatically triggers** via `workflow_run`
4. Deployment gets latest approved model and deploys

**Key Point:** Model approval happens BEFORE deployment triggers, not as the trigger itself.

---

## Related Files

- `.github/workflows/model-build.yml` - Build workflow (approves model)
- `.github/workflows/model-deploy.yml` - Deployment workflow (triggered by build)
- `scripts/approve_model.py` - Approves model in Model Registry
- `scripts/get_latest_model.py` - Gets approved model for deployment
