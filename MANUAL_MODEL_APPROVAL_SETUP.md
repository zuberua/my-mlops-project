# Manual Model Approval in GitHub Actions

## Overview

You can add a manual approval gate for model approval in GitHub Actions, so a human must review model metrics before the model is approved in the Model Registry.

---

## How It Works

### Current Flow (Automatic Approval)
```
Training completes
    ↓
Model registered (PendingManualApproval)
    ↓
Script checks accuracy >= 0.8
    ↓
Model automatically approved
    ↓
Deployment workflow triggers
```

### New Flow (Manual Approval)
```
Training completes
    ↓
Model registered (PendingManualApproval)
    ↓
GitHub Actions PAUSES ⏸️
    ↓
Human reviews metrics in GitHub UI
    ↓
Human approves in GitHub
    ↓
Model approved in Model Registry
    ↓
Deployment workflow triggers
```

---

## Setup Instructions

### Step 1: Create GitHub Environment

1. Go to your GitHub repository
2. Click **Settings** → **Environments**
3. Click **New environment**
4. Name: `model-approval`
5. Under **Deployment protection rules**, check **Required reviewers**
6. Add reviewers (people who can approve models)
7. Click **Save protection rules**

### Step 2: Update Workflow (Already Done)

The workflow has been updated with:
```yaml
environment:
  name: model-approval  # This requires manual approval
```

### Step 3: Test It

1. Push code to trigger the workflow
2. Wait for training to complete
3. Go to **Actions** tab in GitHub
4. You'll see the workflow waiting for approval
5. Click **Review deployments**
6. Review the model metrics displayed
7. Click **Approve and deploy** or **Reject**

---

## What Happens

### When Workflow Runs

1. **Training completes** - Model is trained and evaluated
2. **Metrics displayed** - Accuracy and other metrics shown in GitHub UI
3. **Workflow pauses** - Waits for human approval
4. **Notification sent** - Reviewers get notified
5. **Human reviews** - Reviewer checks metrics
6. **Human approves/rejects** - Decision made in GitHub UI
7. **Model approved** - If approved, model status changes in Model Registry
8. **Deployment triggers** - Deployment workflow starts automatically

### Approval Screen

When the workflow pauses, reviewers see:
```
📊 Model Metrics for Approval

Accuracy: 0.85
Model Package ARN: arn:aws:sagemaker:...
Status: Succeeded

⚠️ Review the metrics above before approving
```

---

## Configuration Options

### Option 1: Automatic Approval (Current - No Manual Gate)

**Use when:**
- You trust the automated accuracy threshold
- You want fast iterations
- You're in development/testing

**Setup:**
```yaml
# No environment specified
register-model:
  name: Register Model
  # No environment = automatic
```

---

### Option 2: Manual Approval (Recommended for Production)

**Use when:**
- You want human oversight
- You're deploying to production
- You need compliance/audit trail

**Setup:**
```yaml
register-model:
  name: Register Model
  environment:
    name: model-approval  # Requires approval
```

---

### Option 3: Conditional Approval

**Use when:**
- Automatic for dev/staging
- Manual for production

**Setup:**
```yaml
register-model:
  name: Register Model
  environment:
    name: ${{ github.ref == 'refs/heads/main' && 'model-approval' || '' }}
    # Manual approval only on main branch
```

---

## Advanced: Multiple Approval Stages

You can have multiple approval gates:

### 1. Model Approval (After Training)
```yaml
register-model:
  environment:
    name: model-approval
```

### 2. Staging Approval (Before Staging Deploy)
```yaml
deploy-staging:
  environment:
    name: staging-approval
```

### 3. Production Approval (Before Production Deploy)
```yaml
deploy-production:
  environment:
    name: production  # Already has approval
```

---

## Approval Workflow Example

### Scenario: New Model Trained

**Time: 10:00 AM** - Developer pushes code
```bash
git push origin main
```

**Time: 10:01 AM** - Build workflow starts
- Creates SageMaker Pipeline
- Starts training

**Time: 10:40 AM** - Training completes
- Model accuracy: 0.87
- Model registered as "PendingManualApproval"

**Time: 10:41 AM** - Workflow pauses for approval
- GitHub sends notification to reviewers
- Metrics displayed in GitHub UI

**Time: 11:00 AM** - Data Scientist reviews
- Checks accuracy: 0.87 ✓
- Checks other metrics
- Reviews training logs

**Time: 11:05 AM** - Data Scientist approves
- Clicks "Approve and deploy" in GitHub

**Time: 11:06 AM** - Model approved
- Model status → "Approved" in Model Registry
- Deployment workflow triggers automatically

**Time: 11:20 AM** - Staging deployed
- Endpoint created
- Tests run automatically

**Time: 11:25 AM** - Production approval needed
- Another manual gate
- DevOps reviews staging results

**Time: 11:30 AM** - Production deployed
- After approval
- Endpoint created with auto-scaling

---

## Notifications

### Email Notifications

Reviewers get email when approval is needed:
```
Subject: Approval needed for model-approval in my-mlops-project

The workflow "Model Build Pipeline" is waiting for approval
in the model-approval environment.

Review and approve: [Link to GitHub]
```

### Slack Notifications (Optional)

You can add Slack notifications:
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Model approval needed",
        "blocks": [{
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "Model trained with accuracy 0.87. Review needed."
          }
        }]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Best Practices

### 1. Clear Approval Criteria

Document what reviewers should check:
- ✅ Accuracy >= 0.85
- ✅ No training errors
- ✅ Data quality checks passed
- ✅ Model size reasonable
- ✅ Training time acceptable

### 2. Multiple Reviewers

Require 2+ reviewers for production:
```
Settings → Environments → model-approval
→ Required reviewers: 2
```

### 3. Timeout

Set a timeout for approvals:
```
Settings → Environments → model-approval
→ Wait timer: 30 minutes
```

### 4. Audit Trail

All approvals are logged:
- Who approved
- When approved
- What was approved

### 5. Reject Option

Reviewers can reject if:
- Accuracy too low
- Training issues found
- Data quality concerns

---

## Troubleshooting

### Workflow Stuck Waiting

**Problem:** Workflow waiting for approval but no notification

**Solution:**
1. Check reviewers are added to environment
2. Check reviewer email settings
3. Manually check Actions tab

### Can't Approve

**Problem:** "Approve" button not showing

**Solution:**
1. Check you're added as a reviewer
2. Check environment protection rules
3. Check you have write access to repo

### Approval Not Working

**Problem:** Approved but workflow not continuing

**Solution:**
1. Check environment name matches exactly
2. Check workflow syntax
3. Check GitHub Actions logs

---

## Comparison

| Aspect | Automatic Approval | Manual Approval |
|--------|-------------------|-----------------|
| **Speed** | Fast (seconds) | Slow (minutes to hours) |
| **Oversight** | None | Human review |
| **Use Case** | Development | Production |
| **Compliance** | Basic | Strong |
| **Audit Trail** | Automated | Human + automated |
| **Risk** | Higher | Lower |

---

## Recommendation

### For Development/Staging
✅ Use **automatic approval**
- Fast iterations
- Trust the accuracy threshold
- No manual overhead

### For Production
✅ Use **manual approval**
- Human oversight
- Compliance requirements
- Risk mitigation
- Better audit trail

---

## Summary

**Manual model approval adds a human review gate before models are approved in the Model Registry.**

**Setup:**
1. Create `model-approval` environment in GitHub
2. Add reviewers
3. Workflow automatically pauses for approval
4. Reviewers see metrics and approve/reject
5. Model approved in Model Registry after approval

**Benefits:**
- Human oversight
- Better compliance
- Audit trail
- Risk mitigation

**Trade-off:**
- Slower (manual review time)
- Requires human availability

Choose based on your needs: automatic for speed, manual for safety.
