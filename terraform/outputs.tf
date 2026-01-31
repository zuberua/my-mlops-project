output "sagemaker_bucket_name" {
  description = "S3 bucket for SageMaker artifacts"
  value       = aws_s3_bucket.sagemaker_bucket.id
}

output "sagemaker_execution_role_arn" {
  description = "SageMaker execution role ARN"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "github_actions_role_arn" {
  description = "GitHub Actions role ARN"
  value       = aws_iam_role.github_actions_role.arn
}

output "model_package_group_name" {
  description = "SageMaker Model Package Group name"
  value       = aws_sagemaker_model_package_group.model_group.model_package_group_name
}

output "model_package_group_arn" {
  description = "SageMaker Model Package Group ARN"
  value       = aws_sagemaker_model_package_group.model_group.arn
}
