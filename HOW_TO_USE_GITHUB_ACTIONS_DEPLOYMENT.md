# How to Use GitHub Actions for Endpoint Deployment

## ✅ Deployment Workflow Exists!

The deployment workflow **is already on GitHub**: `.github/workflows/model-deploy.yml`

---

## 🚀 How to Deploy Using GitHub Actions

### Option 1: Automatic Deployment (After Model Build)

The deployment workflow **automatically triggers** when the model build workflow completes successfully.

**Flow:**
```
Push code to main branch
    ↓
Model Build workflow runs
    ↓
Model trained and approved
    ↓
Model Build workflow completes ✅
    ↓
Model Deploy workflow AUTOMATICALLY triggers
    ↓
Staging deployed (no approval needed)
    ↓
Production deployment waits for approval
```

**To trigger:**
```bash
# Just push code to main branch
git add .
git commit -m "Update model"
git push origin main

# The deployment will happen automatically after build completes
```

---

### Option 2: Manual Deployment (Recommended for Testing)

You can manually trigger the deployment workflow to deploy a specific model.

**Steps:**

1. **Go to GitHub Actions**
   - Navigate to: `https://github.com/YOUR-ORG/YOUR-REPO/actions`
   - Or click the "Actions" tab in your repository

2. **Select the Deployment Workflow**
   - Click on "Model Deployment Pipeline" in the left sidebar

3. **Click "Run workflow"**
   - You'll see a "Run workflow" button on the right

4. **Enter Parameters**
   - **model_package_arn:** `arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1`
   - **environment:** Choose `staging` or `production`

5. **Click "Run workflow"** (green button)

6. **Wait for Deployment**
   - Staging: ~8-10 minutes
   - Production: ~10-15 minutes (requires approval)

---

## 📋 Deployment Workflow Details

### What It Does

**For Staging:**
1. Gets latest approved model from Model Registry
2. Creates SageMaker model
3. Creates endpoint configuration
4. Creates/updates endpoint (ml.m5.xlarge, 1 instance)
5. Waits for endpoint to be ready
6. Runs automated tests
7. Uploads test results

**For Production:**
1. Downloads staging test results
2. Validates staging tests passed
3. **Waits for manual approval** ⏸️
4. Gets latest approved model
5. Creates SageMaker model
6. Creates endpoint configuration
7. Creates/updates endpoint (ml.m5.2xlarge, 2-10 instances with auto-scaling)
8. Waits for endpoint to be ready
9. Runs smoke tests
10. Enables Model Monitor
11. Sends Slack notification (if configured)

---

## 🔍 How to Check if Workflow Exists

### Method 1: GitHub UI
1. Go to your repository on GitHub
2. Click "Actions" tab
3. Look for "Model Deployment Pipeline" in the left sidebar

### Method 2: Check Files
```bash
# List workflow files
ls -la .github/workflows/

# Should show:
# model-build.yml
# model-deploy.yml
```

### Method 3: Git Command
```bash
# Check what's on GitHub
git ls-tree -r origin/main --name-only | grep workflows

# Should show:
# .github/workflows/model-build.yml
# .github/workflows/model-deploy.yml
```

---

## 🎯 Current Situation

### What's on GitHub (origin/main)
✅ `model-build.yml` - Build and training workflow
✅ `model-deploy.yml` - Deployment workflow

### What's Local (not pushed yet)
⚠️ Updated `model-build.yml` with manual approval gate
⚠️ All documentation files (CURRENT_STATUS.md, etc.)

### To Push Updates
```bash
cd my-mlops-project

# Add all changes
git add .

# Commit
git commit -m "Add manual approval gate and comprehensive documentation"

# Push to GitHub
git push origin main
```

---

## 🚀 Deploy Your Model Now

### Quick Deploy via GitHub Actions

1. **Go to GitHub Actions:**
   ```
   https://github.com/YOUR-ORG/YOUR-REPO/actions
   ```

2. **Click "Model Deployment Pipeline"**

3. **Click "Run workflow"**

4. **Enter:**
   - Model ARN: `arn:aws:sagemaker:us-east-1:138720056246:model-package/mlops-demo-model-group/1`
   - Environment: `staging`

5. **Click "Run workflow"**

6. **Monitor Progress:**
   - Click on the running workflow
   - Watch each step complete
   - Check logs if needed

7. **Endpoint Ready:**
   - After ~8-10 minutes
   - Endpoint name: `mlops-demo-staging`
   - Console: https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/endpoints/mlops-demo-staging

---

## 🔧 Troubleshooting

### Issue: "Model Deployment Pipeline" Not Showing

**Possible Causes:**
1. Workflow file not pushed to GitHub
2. Workflow file has syntax errors
3. Looking at wrong branch

**Solution:**
```bash
# Check what's on GitHub
git ls-tree -r origin/main --name-only | grep workflows

# If missing, push it
git add .github/workflows/model-deploy.yml
git commit -m "Add deployment workflow"
git push origin main
```

### Issue: Workflow Fails with "Unable to locate credentials"

**Solution:**
Check GitHub secrets are configured:
- `AWS_ROLE_ARN` - IAM role for OIDC
- `SAGEMAKER_EXECUTION_ROLE_ARN` - SageMaker execution role

### Issue: "Run workflow" Button Not Showing

**Cause:** You need `workflow_dispatch` trigger in the workflow

**Solution:** The workflow already has it! Make sure you're on the "Actions" tab and selected the correct workflow.

---

## 📊 Workflow Triggers

The deployment workflow can be triggered 3 ways:

### 1. Automatic (workflow_run)
```yaml
on:
  workflow_run:
    workflows: ["Model Build Pipeline"]
    types: [completed]
    branches: [main]
```
**When:** After model build completes on main branch

### 2. Manual (workflow_dispatch)
```yaml
on:
  workflow_dispatch:
    inputs:
      model_package_arn: ...
      environment: ...
```
**When:** You click "Run workflow" in GitHub UI

### 3. Repository Dispatch (API)
```yaml
on:
  repository_dispatch:
    types: [model-approved]
```
**When:** External system sends API call to GitHub

---

## 🎉 Summary

**Your deployment workflow IS on GitHub and ready to use!**

**To deploy right now:**
1. Go to GitHub Actions
2. Click "Model Deployment Pipeline"
3. Click "Run workflow"
4. Enter model ARN and environment
5. Click "Run workflow"

**Or deploy locally:**
```bash
./deploy.sh
```

Both methods work! GitHub Actions is better for:
- ✅ Audit trail
- ✅ Approval gates
- ✅ Automated testing
- ✅ Notifications

Local script is better for:
- ✅ Quick testing
- ✅ Debugging
- ✅ One-off deployments
