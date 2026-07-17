
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


# ============================================================
# Workload critical count metric filter
#
# Reads the structured health_check_summary JSON log events
# written by the Health Checker Lambda and extracts the
# critical_count value.
#
# This turns log data into a custom CloudWatch metric that can
# be alarmed on separately from Lambda execution errors.
# ============================================================

resource "aws_cloudwatch_log_metric_filter" "workload_critical_count" {
  name           = "${local.name_prefix}-workload-critical-count"
  log_group_name = aws_cloudwatch_log_group.health_checker.name

  # Match only structured summary log events from the Health Checker Lambda.
  pattern = "{ $.event_type = \"health_check_summary\" }"

  metric_transformation {
    name      = "WorkloadCriticalCount"
    namespace = "CloudOpsIncidentDashboard"

    # Use the critical_count field from the JSON log event as the metric value.
    value = "$.critical_count"

    unit = "Count"
  }
}


# ============================================================
# Workload critical status alarm
#
# Monitors the custom WorkloadCriticalCount metric created from
# Health Checker Lambda structured log events.
#
# This alarm enters ALARM state when one or more monitored
# workloads are reported as critical.
#
# This is different from the Lambda execution error alarm:
# - Lambda error alarm = the monitoring function itself failed
# - Workload critical alarm = a monitored workload failed
# ============================================================

resource "aws_cloudwatch_metric_alarm" "workload_critical_count" {
  alarm_name        = "${local.name_prefix}-workload-critical-count"
  alarm_description = "Alerts when one or more monitored workloads report critical health status."

  namespace   = "CloudOpsIncidentDashboard"
  metric_name = "WorkloadCriticalCount"

  # Use the maximum reported critical count during the period.
  # If any Health Checker run reports 1 or more critical workloads,
  # the alarm should fire.
  statistic = "Maximum"

  # Match the Health Checker schedule, which currently runs once per hour.
  period = 3600

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1

  # Do not alarm just because no recent metric data exists.
  treat_missing_data = "notBreaching"

  # Send workload health alerts to the CloudOps SNS topic.
  alarm_actions = [
    aws_sns_topic.cloudops_alerts.arn
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-workload-critical-count"
  })
}