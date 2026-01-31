# Architecture Diagrams

Visual representations of the SageMaker MLOps pipeline with GitHub Actions.

## 📊 Available Diagrams

All diagrams are located in the `generated-diagrams/` folder.

---

## 1. Complete Architecture Overview

**File:** `mlops-complete-architecture.png`

**Description:** High-level view of the entire MLOps system showing:
- Developer workflow with GitHub
- GitHub Actions CI/CD pipelines (Build and Deploy)
- OIDC authentication flow
- SageMaker ML pipeline components
- Staging and production environments
- Monitoring and observability

**Key Components:**
- GitHub Actions workflows
- IAM roles and OIDC provider
- SageMaker Pipeline (Processing, Training, Evaluation)
- Model Registry
- Staging endpoint (ml.m5.xlarge)
- Production endpoint (ml.m5.2xlarge with autoscaling)
- CloudWatch monitoring

**Use Case:** Understanding the complete system architecture

---

## 2. Model Build Pipeline - Detailed Flow

**File:** `model-build-pipeline-detailed.png`

**Description:** Detailed view of the model training pipeline showing:
- GitHub Actions build workflow steps
- SageMaker Pipeline execution stages
- Data flow through preprocessing, training, and evaluation
- Conditional model registration based on accuracy
- Model Registry integration

**Pipeline Steps:**
1. **Preprocess:** Split data into train/validation/test sets
2. **Train:** Train model with XGBoost (or custom algorithm)
3. **Evaluate:** Calculate metrics on test data
4. **Conditional Register:** Register model if accuracy >= 0.8

**Use Case:** Understanding the model training workflow

---

## 3. Model Deployment Pipeline - Lab 5

**File:** `deployment-pipeline-lab5.png`

**Description:** Complete deployment pipeline showing:
- Deployment trigger from approved model
- Staging deployment with automated testing
- Manual approval gate with GitHub environments
- Production deployment with autoscaling
- Model Monitor setup

**Deployment Flow:**
1. **Staging Deployment:**
   - Get latest approved model
   - Create endpoint (ml.m5.xlarge)
   - Run comprehensive tests
   - Upload test results

2. **Manual Approval:**
   - Notification sent to reviewers
   - Review test results
   - Approve/reject in GitHub UI

3. **Production Deployment:**
   - Validate staging tests
   - Create endpoint (ml.m5.2xlarge, 2-10 instances)
   - Run smoke tests
   - Enable Model Monitor
   - Send notifications

**Use Case:** Understanding Lab 5 deployment pipeline

---

## 4. GitHub Actions vs AWS Native Comparison

**File:** `github-vs-aws-comparison.png`

**Description:** Side-by-side comparison showing:
- **GitHub Actions Approach:** Simple, cost-effective ($0/month)
  - GitHub repo → GitHub Actions → OIDC → SageMaker
  
- **AWS Native Approach:** Complex, costly ($50-100/month)
  - CodeCommit → EventBridge → CodePipeline → CodeBuild → CloudFormation → SageMaker

**Key Differences:**
- Cost: $0 vs $50-100/month
- Complexity: 1 workflow file vs 5 AWS services
- UI: Single GitHub UI vs multiple AWS consoles

**Use Case:** Deciding between GitHub Actions and AWS native

---

## 5. OIDC Authentication Flow

**File:** `oidc-authentication-flow.png`

**Description:** Secure authentication mechanism showing:
- GitHub Actions requests JWT token
- GitHub OIDC provider issues token
- AWS OIDC provider validates token
- AWS STS issues temporary credentials
- Credentials used to access SageMaker

**Security Benefits:**
- ✅ No long-lived AWS credentials
- ✅ No secrets stored in GitHub
- ✅ Temporary credentials only
- ✅ Automatic rotation
- ✅ Least privilege access

**Use Case:** Understanding secure authentication

---

## 6. Data Flow - Training to Production

**File:** `data-flow-training-to-production.png`

**Description:** Complete data flow showing:
- Raw data sources (S3, Feature Store)
- Data preprocessing and splitting
- Model training with train/validation data
- Model evaluation with test data
- Model packaging and registration
- Deployment to staging and production
- Data capture and monitoring

**Data Journey:**
1. Raw data → Preprocessing → Train/Val/Test splits
2. Training data → Model training → Model artifacts
3. Test data + Model → Evaluation → Metrics
4. Model + Metrics → Model Registry
5. Model Registry → Staging/Production endpoints
6. Endpoints → Predictions + Data capture
7. Data capture → Model Monitor → Violations

**Use Case:** Understanding data flow through the system

---

## How to Use These Diagrams

### In Documentation
Reference diagrams in your documentation:
```markdown
![Complete Architecture](generated-diagrams/mlops-complete-architecture.png)
```

### In Presentations
Use diagrams in presentations to explain:
- System architecture to stakeholders
- Deployment process to team members
- Cost comparison to management
- Security model to security team

### In Training
Use diagrams for:
- Onboarding new team members
- Training on MLOps best practices
- Explaining CI/CD workflows
- Teaching SageMaker concepts

---

## Diagram Legend

### Common Icons

**GitHub/CI/CD:**
- 👤 User - Developer
- 📦 General - GitHub, Workflows, Steps
- 🔐 IAM - Authentication, Roles

**AWS Services:**
- 🤖 Sagemaker - SageMaker services
- 📊 SagemakerTrainingJob - Training jobs
- 📦 SagemakerModel - Model packages
- 💾 S3 - Storage buckets
- 🖥️ EC2Instance - Compute instances
- 📈 AutoScaling - Auto scaling groups
- 📊 Cloudwatch - Monitoring
- 📝 CloudwatchLogs - Logs
- 🔔 CloudwatchAlarm - Alarms

**Connections:**
- → Solid arrow - Data/control flow
- ⇢ Labeled arrow - Specific action/condition

---

## Updating Diagrams

To regenerate diagrams with changes:

1. **Install Python diagrams package:**
   ```bash
   pip install diagrams
   ```

2. **Modify diagram code:**
   - Edit the Python code in the generation script
   - Update icons, clusters, or flows

3. **Regenerate:**
   ```bash
   python generate_diagrams.py
   ```

4. **Commit changes:**
   ```bash
   git add generated-diagrams/
   git commit -m "Update architecture diagrams"
   ```

---

## Diagram Details

### Complete Architecture
- **Complexity:** High
- **Detail Level:** Overview
- **Best For:** Executive presentations, documentation

### Model Build Pipeline
- **Complexity:** Medium
- **Detail Level:** Detailed
- **Best For:** Developer training, technical documentation

### Deployment Pipeline
- **Complexity:** Medium
- **Detail Level:** Detailed
- **Best For:** Lab 5 walkthrough, deployment training

### Comparison
- **Complexity:** Low
- **Detail Level:** High-level
- **Best For:** Decision making, cost analysis

### OIDC Flow
- **Complexity:** Low
- **Detail Level:** Focused
- **Best For:** Security reviews, authentication setup

### Data Flow
- **Complexity:** Medium
- **Detail Level:** Detailed
- **Best For:** Data engineering, ML pipeline design

---

## Additional Resources

### AWS Architecture Icons
- [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
- Official AWS icon set for diagrams

### Diagram Tools
- [Diagrams](https://diagrams.mingrammer.com/) - Python library used
- [Draw.io](https://draw.io/) - Alternative diagramming tool
- [Lucidchart](https://lucidchart.com/) - Professional diagramming

### AWS Well-Architected
- [ML Lens](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/)
- Best practices for ML workloads

---

## Quick Reference

| Diagram | Purpose | Audience |
|---------|---------|----------|
| Complete Architecture | System overview | All stakeholders |
| Model Build Pipeline | Training workflow | Data scientists, ML engineers |
| Deployment Pipeline | Deployment process | DevOps, MLOps engineers |
| GitHub vs AWS | Cost/complexity comparison | Management, architects |
| OIDC Flow | Security model | Security team, architects |
| Data Flow | Data journey | Data engineers, ML engineers |

---

## Feedback

If you need additional diagrams or modifications:
1. Open an issue describing the diagram needed
2. Specify the focus area and detail level
3. Indicate the target audience

Common requests:
- Disaster recovery flow
- Multi-region deployment
- A/B testing architecture
- Retraining pipeline
- Cost breakdown diagram
