
# ============================================================
# Package the Health Checker Lambda source code as a ZIP file
#
# Terraform reads health_checker.py and creates the deployment
# package that will be uploaded to AWS Lambda.
# ============================================================

data "archive_file" "health_checker_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_src/health_checker.py"
  output_path = "${path.module}/health_checker.zip"
}


# ============================================================
# CloudWatch log group for the Health Checker Lambda
#
# Creating the log group explicitly allows Terraform to control
# log retention instead of allowing logs to remain indefinitely.
# ============================================================

resource "aws_cloudwatch_log_group" "health_checker" {
  name              = "/aws/lambda/${local.name_prefix}-health-checker"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker-logs"
  })
}


# ============================================================
# Health Checker Lambda function
#
# This Lambda checks the configured workload URLs, determines
# their health status, and writes the latest results to DynamoDB.
# ============================================================

resource "aws_lambda_function" "health_checker" {
  function_name = "${local.name_prefix}-health-checker"

  # IAM execution role used by this Lambda.
  role = aws_iam_role.health_checker_lambda.arn


  # Python file: health_checker.py
  # Function: lambda_handler
  handler = "health_checker.lambda_handler"

  runtime = "python3.11"


  # Lambda deployment package created by archive_file.
  # source_code_hash tells Terraform when the Python code changes
  # so the deployed Lambda code can be updated.
  filename         = data.archive_file.health_checker_zip.output_path
  source_code_hash = data.archive_file.health_checker_zip.output_base64sha256


  # Execution limits for this lightweight health-checking workload.
  timeout     = 30
  memory_size = 128


  # Environment variables passed from Terraform into the Python code.
  environment {
    variables = {
      # DynamoDB table where current workload health results are stored.
      TABLE_NAME = aws_dynamodb_table.cloudops_status.name

      # Convert the Terraform workload list into JSON for Python to read.
      WORKLOADS_JSON = jsonencode(var.workloads)

      # Maximum time allowed for each individual URL health check.
      TIMEOUT_SECONDS = tostring(var.health_check_timeout_seconds)
    }
  }

  # Ensure the log group and required IAM permissions exist before
  # Terraform creates or updates the Lambda function.
  depends_on = [
    aws_cloudwatch_log_group.health_checker,
    aws_iam_role_policy_attachment.health_checker_lambda_basic,
    aws_iam_role_policy.health_checker_dynamodb_write
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker"
  })
}


# ============================================================
# Package the Status API Lambda source code as a ZIP file
# ============================================================

data "archive_file" "status_api_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_src/status_api.py"
  output_path = "${path.module}/status_api.zip"
}


# ============================================================
# CloudWatch log group for the Status API Lambda
#
# Creating the log group explicitly lets Terraform control
# log retention instead of leaving logs indefinitely.
# ============================================================

resource "aws_cloudwatch_log_group" "status_api" {
  name              = "/aws/lambda/${local.name_prefix}-status-api"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status-api-logs"
  })
}


# ============================================================
# Status API Lambda function
#
# This Lambda reads the latest workload health records from
# DynamoDB and returns them as JSON for the dashboard API.
# ============================================================

resource "aws_lambda_function" "status_api" {
  function_name = "${local.name_prefix}-status-api"

  # IAM execution role used by this Lambda.
  role = aws_iam_role.status_api_lambda.arn

  # Python file: status_api.py
  # Function: lambda_handler
  handler = "status_api.lambda_handler"

  runtime = "python3.11"

  # Lambda deployment package created by archive_file.
  filename         = data.archive_file.status_api_zip.output_path
  source_code_hash = data.archive_file.status_api_zip.output_base64sha256

  # Small settings are sufficient for this lightweight read API.
  timeout     = 10
  memory_size = 128

  # Pass the DynamoDB table name into the Python code.
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.cloudops_status.name
    }
  }

  # Ensure supporting resources and permissions exist first.
  depends_on = [
    aws_cloudwatch_log_group.status_api,
    aws_iam_role_policy_attachment.status_api_lambda_basic,
    aws_iam_role_policy.status_api_dynamodb_read
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status-api"
  })
}


# ============================================================
# Default API Gateway stage
#
# The $default stage exposes the API directly from the base
# invoke URL without requiring an extra stage name in the path.
#
# auto_deploy ensures future API changes are deployed
# automatically after Terraform updates the API configuration.
# ============================================================

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.cloudops_api.id

  name        = "$default"
  auto_deploy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-default-stage"
  })
}