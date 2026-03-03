# Deployment Stage - Simple Steps

## What's Involved in Deployment

### Stage 1: Deploy to Staging (Automatic)

1. **Get Latest Approved Model**
   - Query Model Registry for approved model
   - Get model package ARN

2. **Deploy Staging Endpoint**
   - Create SageMaker Model from model package
   - Create Endpoint Config (ml.m5.xlarge, 1 instance)
   - Create/Update Endpoint

3. **Wait for Endpoint**
   - Poll endpoint status every 30 seconds
   - Wait until status = "InService" (~8-10 minutes)

4. **Test Endpoint**
   - Send test requests to endpoint
   - Validate predictions
   - Measure latency (avg, p95, p99)
   - Check accuracy

5. **Save Test Results**
   - Upload test results as artifact

---

### Stage 2: Deploy to Production (After Manual Approval)

6. **Manual Approval Gate**
   - Review staging test results in GitHub UI
   - Approve to proceed

7. **Validate Staging Tests**
   - Download staging test results
   - Verify tests passed
   - Check accuracy >= 0.85

8. **Get Latest Approved Model**
   - Same as step 1

9. **Deploy Production Endpoint**
   - Create SageMaker Model
   - Create Endpoint Config (ml.m5.2xlarge, 2 instances)
   - Create/Update Endpoint
   - Configure Auto Scaling (2-10 instances)

10. **Wait for Endpoint**
    - Poll until "InService" (~10-15 minutes)

11. **Smoke Test Production**
    - Send test requests
    - Validate endpoint works

12. **Enable Model Monitor**
    - Create monitoring schedule (runs hourly)
    - Enable CloudWatch metrics
    - Configure data capture

13. **Notify**
    - Create deployment summary
    - Send Slack notification (optional)

---

## Summary

**Staging:** Get model → Deploy → Wait → Test → Save results
**Production:** Approve → Validate → Deploy → Wait → Test → Monitor → Notify

**Total Time:**
- Staging: ~10-12 minutes
- Production: ~12-15 minutes (after approval)

**What Runs in GitHub Actions:** Python scripts (orchestration)
**What Runs in AWS:** SageMaker endpoints (model serving)
