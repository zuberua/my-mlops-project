# Notebooks for Exploration and Experimentation

This directory contains Jupyter notebooks for exploratory data analysis, prototyping, and experimentation.

## Purpose

- **Exploration**: Understand your data, visualize distributions, find patterns
- **Prototyping**: Try different algorithms, features, hyperparameters
- **Experimentation**: Test ideas before committing to production pipeline

## Notebooks vs Production Pipeline

| Aspect | Notebooks | Production Pipeline |
|--------|-----------|---------------------|
| **Purpose** | Exploration, experimentation | Automated production deployment |
| **Location** | SageMaker Studio | GitHub Actions + SageMaker |
| **Execution** | Manual, interactive | Automatic, triggered by Git |
| **Version Control** | Optional | Required (Git) |
| **Reproducibility** | Low (state dependent) | High (code-based) |
| **When to Use** | Research, prototyping | Production deployments |

## Workflow

1. **Explore in Notebooks** (this directory)
   - Load and analyze data
   - Try different approaches
   - Visualize results
   - Prototype models

2. **Convert to Scripts** (when ready for production)
   - Extract working code from notebooks
   - Convert to Python scripts (.py files)
   - Add to `preprocessing/`, `evaluation/`, etc.
   - Commit to Git

3. **Automate with Pipeline**
   - Push to GitHub
   - GitHub Actions runs automatically
   - Model deployed to production

## Available Notebooks

### 01-data-exploration.ipynb
- Load and explore the dataset
- Visualize distributions
- Identify missing values
- Understand feature relationships

### 02-feature-engineering.ipynb
- Create new features
- Test feature transformations
- Evaluate feature importance
- Prototype preprocessing logic

### 03-model-experimentation.ipynb
- Try different algorithms
- Tune hyperparameters
- Compare model performance
- Select best approach

### 04-model-evaluation.ipynb
- Deep dive into model metrics
- Analyze errors
- Test on different data slices
- Validate model behavior

## Setup SageMaker Studio

### Option 1: Use Existing Studio Domain
```bash
# List existing domains
aws sagemaker list-domains

# Create user profile
aws sagemaker create-user-profile \
  --domain-id <domain-id> \
  --user-profile-name mlops-developer
```

### Option 2: Create New Studio Domain (via Terraform)
See `terraform/sagemaker-studio.tf` for infrastructure code.

## Running Notebooks

### In SageMaker Studio:
1. Open SageMaker Studio
2. Navigate to this directory
3. Open any notebook
4. Select kernel: `Python 3 (Data Science)`
5. Run cells interactively

### Locally (for development):
```bash
# Install dependencies
pip install jupyter notebook sagemaker pandas matplotlib seaborn

# Start Jupyter
jupyter notebook

# Open notebooks in browser
```

## Best Practices

### DO:
✅ Use notebooks for exploration and experimentation
✅ Document your findings in markdown cells
✅ Save interesting visualizations
✅ Commit notebooks to Git (with outputs cleared)
✅ Convert working code to scripts for production

### DON'T:
❌ Use notebooks for production deployments
❌ Commit notebooks with sensitive data
❌ Rely on notebook state for reproducibility
❌ Skip converting to scripts when ready

## Converting Notebooks to Scripts

When you have working code in a notebook:

```bash
# Extract Python code from notebook
jupyter nbconvert --to script 02-feature-engineering.ipynb

# Clean up and move to appropriate directory
# Edit the .py file to remove notebook-specific code
mv 02-feature-engineering.py ../preprocessing/preprocess.py

# Test the script
python ../preprocessing/preprocess.py

# Commit to Git
git add ../preprocessing/preprocess.py
git commit -m "Add feature engineering from notebook experiments"
git push
```

## Sharing Notebooks

### With Team:
- Commit to Git (clear outputs first)
- Share via SageMaker Studio
- Export as HTML for non-technical stakeholders

### Clear Outputs Before Committing:
```bash
# Clear all outputs
jupyter nbconvert --clear-output --inplace *.ipynb

# Or use nbstripout
pip install nbstripout
nbstripout *.ipynb
```

## Resources

- [SageMaker Studio Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/studio.html)
- [Jupyter Notebook Best Practices](https://jupyter-notebook.readthedocs.io/)
- [Converting Notebooks to Scripts](https://nbconvert.readthedocs.io/)
