#!/usr/bin/env python3
"""Create or update SageMaker Pipeline."""

import argparse
import json
import boto3
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, CreateModelStep
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.properties import PropertyFile
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker import get_execution_role


def create_pipeline(
    region,
    role,
    project_name,
    bucket=None,
):
    """Create SageMaker Pipeline."""
    
    sagemaker_session = boto3.Session(region_name=region)
    sm_client = sagemaker_session.client("sagemaker")
    
    if bucket is None:
        bucket = f"sagemaker-{region}-{boto3.client('sts').get_caller_identity()['Account']}"
    
    # Pipeline parameters
    processing_instance_type = ParameterString(
        name="ProcessingInstanceType",
        default_value="ml.m5.xlarge"
    )
    
    training_instance_type = ParameterString(
        name="TrainingInstanceType",
        default_value="ml.m5.xlarge"
    )
    
    model_approval_status = ParameterString(
        name="ModelApprovalStatus",
        default_value="PendingManualApproval"
    )
    
    input_data = ParameterString(
        name="InputData",
        default_value=f"s3://{bucket}/{project_name}/input/data.csv"
    )
    
    # Step 1: Data preprocessing
    sklearn_processor = SKLearnProcessor(
        framework_version="1.2-1",
        instance_type=processing_instance_type,
        instance_count=1,
        base_job_name=f"{project_name}-preprocess",
        role=role,
    )
    
    step_process = ProcessingStep(
        name="PreprocessData",
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(
                source=input_data,
                destination="/opt/ml/processing/input"
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="train",
                source="/opt/ml/processing/train",
                destination=f"s3://{bucket}/{project_name}/train"
            ),
            ProcessingOutput(
                output_name="validation",
                source="/opt/ml/processing/validation",
                destination=f"s3://{bucket}/{project_name}/validation"
            ),
            ProcessingOutput(
                output_name="test",
                source="/opt/ml/processing/test",
                destination=f"s3://{bucket}/{project_name}/test"
            ),
        ],
        code="preprocessing/preprocess.py",
    )
    
    # Step 2: Model training
    estimator = Estimator(
        image_uri=f"683313688378.dkr.ecr.{region}.amazonaws.com/sagemaker-xgboost:1.5-1",
        instance_type=training_instance_type,
        instance_count=1,
        output_path=f"s3://{bucket}/{project_name}/models",
        base_job_name=f"{project_name}-train",
        role=role,
        hyperparameters={
            "objective": "binary:logistic",
            "num_round": "100",
            "max_depth": "5",
            "eta": "0.2",
            "subsample": "0.8",
            "colsample_bytree": "0.8",
        },
    )
    
    step_train = TrainingStep(
        name="TrainModel",
        estimator=estimator,
        inputs={
            "train": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri,
                content_type="text/csv"
            ),
            "validation": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri,
                content_type="text/csv"
            ),
        },
    )
    
    # Step 3: Model evaluation
    evaluation_processor = SKLearnProcessor(
        framework_version="1.2-1",
        instance_type=processing_instance_type,
        instance_count=1,
        base_job_name=f"{project_name}-evaluate",
        role=role,
    )
    
    evaluation_report = PropertyFile(
        name="EvaluationReport",
        output_name="evaluation",
        path="evaluation.json"
    )
    
    step_evaluate = ProcessingStep(
        name="EvaluateModel",
        processor=evaluation_processor,
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model"
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs["test"].S3Output.S3Uri,
                destination="/opt/ml/processing/test"
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation",
                destination=f"s3://{bucket}/{project_name}/evaluation"
            ),
        ],
        code="evaluation/evaluate.py",
        property_files=[evaluation_report],
    )
    
    # Step 4: Register model (conditional)
    from sagemaker.workflow.functions import Join
    
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=Join(
                on="/",
                values=[
                    step_evaluate.properties.ProcessingOutputConfig.Outputs['evaluation'].S3Output.S3Uri,
                    "evaluation.json"
                ]
            ),
            content_type="application/json"
        )
    )
    
    step_register = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.t2.medium", "ml.m5.xlarge"],
        transform_instances=["ml.m5.xlarge"],
        model_package_group_name=f"{project_name}-model-group",
        approval_status=model_approval_status,
        model_metrics=model_metrics,
    )
    
    # Condition: Register model only if accuracy >= 0.8
    cond_gte = ConditionGreaterThanOrEqualTo(
        left=evaluation_report.get("classification_metrics.accuracy.value"),
        right=0.8
    )
    
    step_cond = ConditionStep(
        name="CheckAccuracy",
        conditions=[cond_gte],
        if_steps=[step_register],
        else_steps=[],
    )
    
    # Create pipeline
    pipeline = Pipeline(
        name=f"{project_name}-pipeline",
        parameters=[
            processing_instance_type,
            training_instance_type,
            model_approval_status,
            input_data,
        ],
        steps=[step_process, step_train, step_evaluate, step_cond],
    )
    
    # Create or update pipeline
    pipeline.upsert(role_arn=role)
    
    # Save pipeline ARN
    with open("pipeline_arn.txt", "w") as f:
        f.write(pipeline.describe()["PipelineArn"])
    
    print(f"Pipeline created/updated: {pipeline.name}")
    print(f"Pipeline ARN: {pipeline.describe()['PipelineArn']}")
    
    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", type=str, required=True)
    parser.add_argument("--role", type=str, required=True)
    parser.add_argument("--project-name", type=str, required=True)
    parser.add_argument("--bucket", type=str, default=None)
    
    args = parser.parse_args()
    
    create_pipeline(
        region=args.region,
        role=args.role,
        project_name=args.project_name,
        bucket=args.bucket,
    )
