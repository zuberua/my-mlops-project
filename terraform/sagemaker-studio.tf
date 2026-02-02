# Optional: SageMaker Studio for notebook-based exploration
# Uncomment this file if you want to create SageMaker Studio

# Note: This is separate from the automated pipeline
# Studio is for exploration/experimentation, pipeline is for production

/*
# VPC for SageMaker Studio (optional - can use default VPC)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# SageMaker Studio Domain
resource "aws_sagemaker_domain" "studio" {
  domain_name = "${var.project_name}-studio"
  auth_mode   = "IAM"
  vpc_id      = data.aws_vpc.default.id
  subnet_ids  = data.aws_subnets.default.ids

  default_user_settings {
    execution_role = aws_iam_role.sagemaker_execution_role.arn

    jupyter_server_app_settings {
      default_resource_spec {
        instance_type       = "system"
        sagemaker_image_arn = "arn:aws:sagemaker:${var.aws_region}:081325390199:image/jupyter-server-3"
      }
    }

    kernel_gateway_app_settings {
      default_resource_spec {
        instance_type       = "ml.t3.medium"
        sagemaker_image_arn = "arn:aws:sagemaker:${var.aws_region}:081325390199:image/datascience-1.0"
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-studio"
    Environment = "development"
    Purpose     = "exploration-and-experimentation"
  }
}

# User Profile for Studio
resource "aws_sagemaker_user_profile" "developer" {
  domain_id         = aws_sagemaker_domain.studio.id
  user_profile_name = "mlops-developer"

  user_settings {
    execution_role = aws_iam_role.sagemaker_execution_role.arn
  }

  tags = {
    Name = "mlops-developer"
  }
}

# Output Studio URL
output "sagemaker_studio_url" {
  description = "SageMaker Studio URL"
  value       = "https://${aws_sagemaker_domain.studio.domain_id}.studio.${var.aws_region}.sagemaker.aws/jupyter/default"
}

output "sagemaker_studio_domain_id" {
  description = "SageMaker Studio Domain ID"
  value       = aws_sagemaker_domain.studio.id
}

output "sagemaker_user_profile" {
  description = "SageMaker User Profile Name"
  value       = aws_sagemaker_user_profile.developer.user_profile_name
}
*/
