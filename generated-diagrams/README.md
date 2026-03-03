# Generated Diagrams

This folder contains all architecture diagrams for the MLOps project.

---

## Lab 5 Deployment Pipeline - Multiple Versions

We provide **4 versions** of the Lab 5 deployment diagram. Choose based on your needs:

### ⭐ lab5-final.png (RECOMMENDED)
- **Size:** 155 KB
- **Style:** Simple vertical flow
- **Best for:** Presentations, quick understanding
- **Audience:** Everyone

### lab5-stepbystep.png
- **Size:** 125 KB
- **Style:** Horizontal step-by-step
- **Best for:** Training, tutorials
- **Audience:** Learners

### lab5-deployment-clear.png
- **Size:** 239 KB
- **Style:** Vertical with more detail
- **Best for:** Technical documentation
- **Audience:** Developers

### lab5-deployment-pipeline.png (Original)
- **Size:** 277 KB
- **Style:** Comprehensive with all components
- **Best for:** Complete technical reference
- **Audience:** Technical experts

**See [DIAGRAM_GUIDE.md](../DIAGRAM_GUIDE.md) for detailed selection guide.**

---

## Other Diagrams

### Lab 4 - Model Build Pipeline
- **lab4-model-build-pipeline.png** (259 KB)
- Shows the training pipeline with SageMaker

### Complete Architecture
- **complete-mlops-architecture-github.png** (400 KB)
- End-to-end system architecture

### Legacy Diagrams
- **mlops-complete-architecture.png** (399 KB)
- **model-build-pipeline-detailed.png** (359 KB)
- **deployment-pipeline-lab5.png** (163 KB)
- **github-sagemaker-oidc-connection.png**
- **github-sagemaker-oidc-detailed.png**
- **github-vs-aws-comparison.png**
- **oidc-authentication-flow.png**
- **data-flow-training-to-production.png**

---

## Quick Reference

| Diagram | Purpose | Size |
|---------|---------|------|
| lab5-final.png ⭐ | Deployment (simple) | 155 KB |
| lab5-stepbystep.png | Deployment (steps) | 125 KB |
| lab5-deployment-clear.png | Deployment (detailed) | 239 KB |
| lab5-deployment-pipeline.png | Deployment (complete) | 277 KB |
| lab4-model-build-pipeline.png | Training pipeline | 259 KB |
| complete-mlops-architecture-github.png | Full system | 400 KB |

---

## Usage in Markdown

```markdown
# Simple deployment flow
![Deployment](generated-diagrams/lab5-final.png)

# Step-by-step deployment
![Deployment Steps](generated-diagrams/lab5-stepbystep.png)

# Training pipeline
![Training](generated-diagrams/lab4-model-build-pipeline.png)

# Complete architecture
![Architecture](generated-diagrams/complete-mlops-architecture-github.png)
```

---

## Regenerating Diagrams

If you need to update diagrams, use the AWS Diagram MCP server:

```python
# See LAB_DIAGRAMS.md for diagram generation code
```

All diagrams are generated using the `diagrams` Python library with AWS icons.
