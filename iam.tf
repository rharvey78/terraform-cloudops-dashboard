
resource "aws_iam_role" "health_checker_lambda" {
  name = "${local.name_prefix}-health-checker-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker-lambda-role"
  })
}

resource "aws_iam_role_policy_attachment" "health_checker_lambda_basic" {
  role       = aws_iam_role.health_checker_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "health_checker_dynamodb_write" {
  name = "${local.name_prefix}-health-checker-dynamodb-write"
  role = aws_iam_role.health_checker_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowWriteHealthCheckResults"
        Effect = "Allow"

        Action = [
          "dynamodb:PutItem"
        ]

        Resource = aws_dynamodb_table.cloudops_status.arn
      }
    ]
  })
}

# Allow the CloudOps Health Checker Lambda to read CloudWatch alarm state.
#
# This permission will be used by operational health checks such as the
# weather data pipeline. The Lambda will inspect existing CloudWatch alarms
# instead of calling the workload's data API and causing a Timestream query.
#
# DescribeAlarms is read-only. It does not allow the Lambda to create,
# modify, disable, or delete CloudWatch alarms.

resource "aws_iam_role_policy" "health_checker_cloudwatch_read" {
  name = "${local.name_prefix}-health-checker-cloudwatch-read"
  role = aws_iam_role.health_checker_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowDescribeCloudWatchAlarms"
        Effect = "Allow"

        Action = [
          "cloudwatch:DescribeAlarms"
        ]

        Resource = "*"
      }
    ]
  })
}

# DynamoDB permissions for Lambda
resource "aws_iam_role" "status_api_lambda" {
  name = "${local.name_prefix}-status-api-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status-api-lambda-role"
  })
}


resource "aws_iam_role_policy_attachment" "status_api_lambda_basic" {
  role       = aws_iam_role.status_api_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_iam_role_policy" "status_api_dynamodb_read" {
  name = "${local.name_prefix}-status-api-dynamodb-read"
  role = aws_iam_role.status_api_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowReadStatusTable"
        Effect = "Allow"

        Action = [
          "dynamodb:Scan"
        ]

        Resource = aws_dynamodb_table.cloudops_status.arn
      }
    ]
  })
}