
data "archive_file" "health_checker_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_src/health_checker.py"
  output_path = "${path.module}/health_checker.zip"
}

resource "aws_cloudwatch_log_group" "health_checker" {
  name              = "/aws/lambda/${local.name_prefix}-health-checker"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker-logs"
  })
}

resource "aws_lambda_function" "health_checker" {
  function_name = "${local.name_prefix}-health-checker"
  role          = aws_iam_role.health_checker_lambda.arn
  handler       = "health_checker.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.health_checker_zip.output_path
  source_code_hash = data.archive_file.health_checker_zip.output_base64sha256

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      TABLE_NAME      = aws_dynamodb_table.cloudops_status.name
      WORKLOADS_JSON  = jsonencode(var.workloads)
      TIMEOUT_SECONDS = tostring(var.health_check_timeout_seconds)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.health_checker,
    aws_iam_role_policy_attachment.health_checker_lambda_basic,
    aws_iam_role_policy.health_checker_dynamodb_write
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker"
  })
}