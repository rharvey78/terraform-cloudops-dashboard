
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