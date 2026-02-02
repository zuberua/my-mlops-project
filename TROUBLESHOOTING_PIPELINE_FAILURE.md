# Troubleshooting Pipeline Failure

## Current Status
✅ GitHub Actions workflow successfully created SageMaker Pipeline
✅ Pipeline execution started
❌ Pipeline failed at PreprocessData step

## How to View Pipeline in AWS Console

### Method 1: SageMaker Console
1. Go to: https://console.aws.amazon.com/sagemaker/
2. Click **Pipelines** in left sidebar
3. Click **mlops-demo-pipeline**
4. Click on the failed execution
5. Click on the **PreprocessData** step (red/failed)
6. View error details and logs

### Method 2: CloudWatch Logs
1. Go to: https://console.aws.amazon.com/cloudwatch/
2. Click **Log groups**
3. Search for: `/aws/sagemaker/ProcessingJobs`
4. Find log stream for: `pipelines-sz7k981aij3b-PreprocessData-Jsgr4oAx6i`
5. View detailed error logs

### Method 3: CLI Commands

```bash
# List pipeline executions
aws sagemaker list-pipeline-executions \
  --pipeline-name mlops-demo-pipeline \
  --sort-by CreationTime \
  --sort-order Descending

# Get execution details
aws sagemaker list-pipeline-execution-steps \
  --pipeline-execution-arn "arn:aws:sagemaker:us-east-1:138720056246:pipeline/mlops-demo-pipeline/execution/sz7k981aij3b"

# Get processing job details
aws sagemaker describe-processing-job \
  --processing-job-name "pipelines-sz7k981aij3b-PreprocessData-Jsgr4oAx6i"

# View CloudWatch logs
aws logs tail /aws/sagemaker/ProcessingJobs \
  --log-stream-name-prefix pipelines-sz7k981aij3b-PreprocessData \
  --follow
```

## Likely Issues

### 1. Input Data Not Found
**Problem**: The preprocessing script expects data at `/opt/ml/processing/input/data.csv`

**Check**:
```bash
# Verify data exists in S3
aws s3 ls s3://sagemaker-mlops-demo-138720056246/mlops-demo/input/
```

**Solution**: Ensure data was uploaded correctly

### 2. Script Dependencies Missing
**Problem**: The SKLearnProcessor might not have all required packages

**Solution**: The script uses pandas and sklearn which should be included in the SKLearnProcessor image

### 3. Script Execution Error
**Problem**: Python error in the preprocessing script

**Solution**: Check CloudWatch logs for Python traceback

## Next Steps

1. **View CloudWatch Logs** (Most Important)
   ```bash
   aws logs tail /aws/sagemaker/ProcessingJobs \
     --log-stream-name-prefix pipelines-sz7k981aij3b-PreprocessData \
     --follow
   ```

2. **Verify S3 Data**
   ```bash
   aws s3 ls s3://sagemaker-mlops-demo-138720056246/mlops-demo/input/
   aws s3 cp s3://sagemaker-mlops-demo-138720056246/mlops-demo/input/data.csv - | head
   ```

3. **Check Processing Job Details**
   ```bash
   aws sagemaker describe-processing-job \
     --processing-job-name "pipelines-sz7k981aij3b-PreprocessData-Jsgr4oAx6i" \
     --query '[FailureReason, ProcessingInputs, ProcessingOutputConfig]'
   ```

## Common Fixes

### If data file not found:
```bash
# Re-upload data
aws s3 cp sample_data.csv s3://sagemaker-mlops-demo-138720056246/mlops-demo/input/data.csv
```

### If script has errors:
1. Fix the script locally
2. Test it locally with sample data
3. Commit and push changes
4. Re-run the workflow

### If permissions issue:
Check that SageMaker execution role has S3 access:
```bash
aws iam get-role-policy \
  --role-name mlops-demo-sagemaker-execution-role \
  --policy-name mlops-demo-sagemaker-s3-access
```

## Re-running the Pipeline

After fixing the issue:

### Option 1: Via GitHub Actions
```bash
# Make a small change to trigger workflow
echo "# Fix applied" >> README.md
git add README.md
git commit -m "Trigger pipeline after fix"
git push
```

### Option 2: Via CLI
```bash
aws sagemaker start-pipeline-execution \
  --pipeline-name mlops-demo-pipeline \
  --pipeline-execution-display-name "manual-retry"
```

### Option 3: Via Console
1. Go to SageMaker → Pipelines → mlops-demo-pipeline
2. Click **Create execution**
3. Click **Start**

