
# ============================================================
# API Gateway access log group
#
# Stores one access log entry for each request made to the
# CloudOps HTTP API.
#
# The $default API Gateway stage will be configured separately
# to send its access logs to this log group.
# ============================================================

resource "aws_cloudwatch_log_group" "api_access_logs" {
  name              = "/aws/apigateway/${local.name_prefix}-access"
  retention_in_days = var.log_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-access-logs"
  })
}


# ============================================================
# Health Checker Lambda execution error alarm
#
# Monitors the AWS/Lambda Errors metric for the Health Checker
# function. The alarm enters ALARM state if one or more Lambda
# execution errors occur during the evaluation period.
#
# This detects failures in the Lambda function itself, such as
# unhandled Python exceptions or runtime errors. It does not
# detect an unhealthy monitored workload.
# ============================================================

resource "aws_cloudwatch_metric_alarm" "health_checker_lambda_errors" {
  alarm_name        = "${local.name_prefix}-health-checker-errors"
  alarm_description = "Alerts when the Health Checker Lambda has one or more execution errors."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"

  # Add together all Lambda errors during each evaluation period.
  statistic = "Sum"

  # Evaluate the metric over a one-hour period because the
  # Health Checker currently runs once per hour.
  period = 3600

  evaluation_periods = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1

  # Do not alarm simply because no metric data exists.
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.health_checker.function_name
  }

  # Send the alarm notification to the CloudOps SNS topic.
  alarm_actions = [
    aws_sns_topic.cloudops_alerts.arn
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-checker-errors"
  })
}