# Using Notebooks with Automated Pipeline

## Overview

This project uses a **hybrid approach**:
- **Notebooks** for exploration and experimentation
- **Automated pipeline** for production deployments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Workflow                      │
└─────────────────────────────────────────────────────────────┘

1. EXPLORATION (Notebooks)
   ├── SageMaker Studio
   ├── Jupyter notebooks
   ├── Interactive analysis
   └── Rapid prototyping

2. CONVERSION (Manual)
   ├── Extract working code
   ├── Convert to Python scripts
   ├── Add tests
   └── Commit to Git

3. PRODUCTION (Automated)
   ├── GitHub Actions
   ├── SageMaker Pipeline
   ├── Automated deployment
   └── Monitoring

```

## When to Use Each

### Use Notebooks For:
✅ **Exploratory Data Analysis (EDA)**
- Understanding your data
- Finding patterns and anomalies
- Visualizing distributions
- Identifying data quality issues

✅ **Prototyping**
- Trying different algorithms
- Testing feature engineering ideas
- Experimenting with hyperparameters
- Quick iterations

✅ **Research**
- Literature review
- Proof of concepts
- Comparing approaches
- Documenting findings

✅ **Debugging**
- Investigating model errors
- Analyzing predictions
- Understanding model behavior
- Testing edge cases

### Use Automated Pipeline For:
✅ **Production Deployments**
- Consistent, reproducible training
- Automated model registration
- Staging and production endpoints
- CI/CD integration

✅ **Scheduled Retraining**
- Automatic model updates
- Data drift detection
- Performance monitoring
- Version control

✅ **Team Collaboration**
- Code reviews via pull requests
- Shared codebase
- Standardized processes
- Audit trail

## Setup Options

### Option 1: Use SageMaker Studio (Recommended)

**Pros:**
- Integrated with AWS
- Pre-configured environments
- Easy access to S3 data
- Built-in Git integration

**Setup:**
```bash
# Uncomment terraform/sagemaker-studio.tf
# Then apply
cd terraform
terraform apply

# Get Studio URL from output
terraform output sagemaker_studio_url
```

**Access:**
1. Go to AWS Console → SageMaker → Studio
2. Click "Open Studio"
3. Clone your Git repository
4. Open notebooks in `notebooks/` directory

### Option 2: Use Local Jupyter

**Pros:**
- Work offline
- Use your own tools
- No AWS costs for notebooks

**Setup:**
```bash
# Install Jupyter
pip install jupyter notebook

# Install dependencies
pip install -r requirements.txt

# Start Jupyter
jupyter notebook

# Open notebooks in browser
```

**Note:** You'll need AWS credentials configured locally to access S3 data.

### Option 3: Use SageMaker Notebook Instances (Legacy)

**Pros:**
- Simpler than Studio
- Lower cost
- Good for individual work

**Setup:**
```bash
# Create notebook instance
aws sagemaker create-notebook-instance \
  --notebook-instance-name mlops-notebook \
  --instance-type ml.t3.medium \
  --role-arn <sagemaker-execution-role-arn>

# Wait for it to be InService
aws sagemaker describe-notebook-instance \
  --notebook-instance-name mlops-notebook

# Get URL
aws sagemaker create-presigned-notebook-instance-url \
  --notebook-instance-name mlops-notebook
```

## Workflow Example

### Step 1: Explore in Notebook

```python
# In notebooks/01-data-exploration.ipynb

import pandas as pd
import sagemaker

# Load data
session = sagemaker.Session()
bucket = session.default_bucket()
df = pd.read_csv(f's3://{bucket}/mlops-demo/input/data.csv')

# Explore
print(df.describe())
df.hist(figsize=(15, 10))

# Find insights
# - Feature X is highly correlated with target
# - Feature Y has missing values
# - Need to normalize features
```

### Step 2: Prototype Solution

```python
# In notebooks/02-feature-engineering.ipynb

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

# Test preprocessing approach
imputer = SimpleImputer(strategy='mean')
scaler = StandardScaler()

X_clean = imputer.fit_transform(X)
X_scaled = scaler.fit_transform(X_clean)

# Validate approach works
print("Preprocessing successful!")
```

### Step 3: Convert to Production Script

```python
# Create preprocessing/preprocess.py

#!/usr/bin/env python3
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

def preprocess_data(input_path, output_path):
    """Preprocess data for training."""
    
    # Load data
    df = pd.read_csv(input_path)
    
    # Apply preprocessing (from notebook experiments)
    imputer = SimpleImputer(strategy='mean')
    scaler = StandardScaler()
    
    X = df.drop('target', axis=1)
    y = df['target']
    
    X_clean = imputer.fit_transform(X)
    X_scaled = scaler.fit_transform(X_clean)
    
    # Save processed data
    # ... (split train/val/test and save)

if __name__ == "__main__":
    # Parse arguments and run
    preprocess_data(input_path, output_path)
```

### Step 4: Commit and Deploy

```bash
# Add the new script
git add preprocessing/preprocess.py

# Commit with reference to notebook
git commit -m "Add preprocessing logic from notebook experiments

Based on findings in notebooks/02-feature-engineering.ipynb:
- Impute missing values with mean
- Standardize features
- Validated on sample data"

# Push to trigger automated pipeline
git push origin main
```

### Step 5: Monitor Production

```python
# In notebooks/04-model-evaluation.ipynb

# After model is deployed, analyze production performance
import boto3

runtime = boto3.client('sagemaker-runtime')

# Test endpoint
response = runtime.invoke_endpoint(
    EndpointName='mlops-demo-production',
    Body=test_data,
    ContentType='text/csv'
)

# Analyze results
predictions = json.loads(response['Body'].read())
# ... deep dive into model behavior
```

## Best Practices

### Notebook Organization

```
notebooks/
├── 01-data-exploration.ipynb       # EDA
├── 02-feature-engineering.ipynb    # Feature experiments
├── 03-model-experimentation.ipynb  # Algorithm testing
├── 04-model-evaluation.ipynb       # Deep dive analysis
├── 05-hyperparameter-tuning.ipynb  # HPO experiments
└── README.md                        # This guide
```

### Notebook Hygiene

**DO:**
✅ Clear outputs before committing
✅ Document findings in markdown cells
✅ Use meaningful variable names
✅ Save important visualizations
✅ Reference notebooks in commit messages

**DON'T:**
❌ Commit notebooks with sensitive data
❌ Rely on notebook state for reproducibility
❌ Use notebooks for production code
❌ Commit large outputs or images
❌ Skip converting to scripts when ready

### Git Integration

```bash
# Install nbstripout to auto-clear outputs
pip install nbstripout

# Configure for your repo
nbstripout --install

# Now git will automatically clear outputs on commit
git add notebooks/*.ipynb
git commit -m "Add exploration notebooks"
```

## Sharing Notebooks

### With Technical Team
```bash
# Commit to Git (outputs cleared)
git add notebooks/
git commit -m "Add EDA findings"
git push
```

### With Non-Technical Stakeholders
```bash
# Export as HTML
jupyter nbconvert --to html notebooks/01-data-exploration.ipynb

# Share the HTML file
# Or upload to S3 for sharing
aws s3 cp notebooks/01-data-exploration.html \
  s3://your-bucket/reports/
```

### In SageMaker Studio
- Use Studio's built-in sharing features
- Share via Studio domain
- Export as PDF for presentations

## Cost Optimization

### SageMaker Studio
- **Cost:** ~$0.05/hour for ml.t3.medium
- **Tip:** Stop kernels when not in use
- **Tip:** Use smaller instances for EDA

### Notebook Instances
- **Cost:** ~$0.05/hour for ml.t3.medium
- **Tip:** Stop instance when not working
- **Tip:** Use lifecycle configs for auto-stop

### Local Jupyter
- **Cost:** $0 (runs on your machine)
- **Tip:** Best for offline work

## Troubleshooting

### Can't Access S3 Data
```python
# Check credentials
import boto3
sts = boto3.client('sts')
print(sts.get_caller_identity())

# Check bucket access
s3 = boto3.client('s3')
s3.list_objects_v2(Bucket='your-bucket', MaxKeys=1)
```

### Kernel Crashes
- Reduce data size for exploration
- Use sampling for large datasets
- Increase instance size if needed

### Git Conflicts with Notebooks
```bash
# Use nbdime for better notebook diffs
pip install nbdime
nbdime config-git --enable --global

# Now git diff shows readable notebook changes
```

## Resources

- [SageMaker Studio Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/studio.html)
- [Jupyter Best Practices](https://jupyter-notebook.readthedocs.io/)
- [nbstripout](https://github.com/kynan/nbstripout)
- [nbdime](https://nbdime.readthedocs.io/)

## Summary

**Notebooks = Exploration & Experimentation**
- Interactive, visual, rapid iteration
- Perfect for research and prototyping
- Not for production deployments

**Automated Pipeline = Production**
- Reproducible, tested, version-controlled
- Perfect for production deployments
- Triggered automatically by Git

**Best of Both Worlds:**
- Explore in notebooks
- Convert to scripts
- Deploy via pipeline
- Monitor with notebooks

This hybrid approach gives you the flexibility of notebooks with the reliability of automated pipelines!
