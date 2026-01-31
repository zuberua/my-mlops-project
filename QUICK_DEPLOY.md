# Quick Deployment Checklist

Fast-track deployment guide. Follow these steps in order.

## ✅ Pre-Deployment (Already Done)

- [x] GitHub to AWS OIDC connection created

## 📋 Deployment Steps

### 1. Deploy Infrastructure (5 minutes)

```bash
cd sagemaker-mlops-github/terraform

# Create config file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
# Set: github_org, github_repo
# Set: create_github_oidc_provider = false

# Deploy
terraform init
terraform apply
# Type: yes

# Save outputs
terraform output > ../terraform-outputs.txt
```

**Outputs you need:**
- `github_actions_role_arn`
- `sagemaker_execution_role_arn`

---

### 2. Configure GitHub (3 minutes)

**Add Secrets:**
1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add `AWS_ROLE_ARN` (from terraform output)
3. Add `SAGEMAKER_EXECUTION_ROLE_ARN` (from terraform output)

**Create Environments:**
1. Settings → Environments → New environment
2. Create `staging` (no protection)
3. Create `production` (enable "Required reviewers", add yourself)

**Enable Permissions:**
1. Settings → Actions → General → Workflow permissions
2. Select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"
4. Save

---

### 3. Upload Sample Data (2 minutes)

```bash
cd ..  # Back to sagemaker-mlops-github/

# Create sample data
cat > sample_data.csv << 'EOF'
feature1,feature2,feature3,feature4,target
0.5,0.3,0.8,0.2,1
0.1,0.2,0.1,0.3,0
0.7,0.6,0.9,0.8,1
0.2,0.1,0.2,0.1,0
0.6,0.5,0.7,0.6,1
EOF

# Upload to S3
BUCKET=$(cd terraform && terraform output -raw sagemaker_bucket_name)
aws s3 cp sample_data.csv s3://${BUCKET}/mlops-demo/input/data.csv
```

---

### 4. Push Code (1 minute)

```bash
# If not already a git repo
git init
git add .
git commit -m "Initial MLOps setup"

# Push to GitHub
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git branch -M main
git push -u origin main
```

**This triggers the pipeline automatically!**

---

### 5. Monitor Build (15-20 minutes)

1. Go to GitHub → Actions tab
2. Click "Model Build Pipeline"
3. Watch it run (takes ~15-20 minutes)

**Expected result:**
- ✅ Pipeline created
- ✅ Model trained
- ✅ Model evaluated
- ✅ Model registered
- ✅ Model approved

---

### 6. Monitor Deployment (10-15 minutes)

**Staging (automatic):**
1. Watch "Model Deployment Pipeline" workflow
2. Staging deploys automatically (~10 minutes)
3. Tests run automatically

**Production (manual approval):**
1. Click "Review deployments"
2. Select "production"
3. Click "Approve and deploy"
4. Production deploys (~10 minutes)

---

### 7. Verify (2 minutes)

```bash
# Check endpoints
aws sagemaker list-endpoints

# Test staging
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name mlops-demo-staging \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt && cat output.txt

# Test production
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name mlops-demo-production \
  --content-type text/csv \
  --body "0.5,0.3,0.8,0.2" \
  output.txt && cat output.txt
```

---

## ⏱️ Total Time: ~40 minutes

- Infrastructure: 5 min
- GitHub config: 3 min
- Data upload: 2 min
- Code push: 1 min
- Build pipeline: 15-20 min
- Deployment: 10-15 min
- Verification: 2 min

---

## 🚨 Common Issues

### "Not authorized to perform sts:AssumeRoleWithWebIdentity"

```bash
# Check trust policy includes your repo
aws iam get-role --role-name mlops-demo-github-actions-role
```

### "Pipeline execution failed"

```bash
# Check logs in GitHub Actions
# Check CloudWatch logs
aws logs tail /aws/sagemaker/ProcessingJobs --follow
```

### "Endpoint deployment failed"

```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name mlops-demo-staging
```

---

## ✅ Success Checklist

- [ ] Terraform applied successfully
- [ ] GitHub secrets added
- [ ] GitHub environments created
- [ ] Sample data in S3
- [ ] Code pushed to GitHub
- [ ] Build workflow completed
- [ ] Staging endpoint deployed
- [ ] Production approved
- [ ] Production endpoint deployed
- [ ] Both endpoints tested

---

## 🎉 Done!

Your MLOps pipeline is now running!

**Next:**
- Customize preprocessing/training/evaluation
- Add more test cases
- Setup CloudWatch alarms
- Configure Slack notifications

**Full guide:** [DEPLOYMENT_STEPS.md](DEPLOYMENT_STEPS.md)
