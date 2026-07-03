
resource "aws_cloudwatch_event_rule" "health_check_schedule" {
  name                = "${local.name_prefix}-health-check-schedule"
  description         = "Runs the CloudOps health checker Lambda on a recurring schedule."
  schedule_expression = var.health_check_schedule

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-check-schedule"
  })
}

resource "aws_cloudwatch_event_target" "health_checker_lambda" {
  rule      = aws_cloudwatch_event_rule.health_check_schedule.name
  target_id = "${local.name_prefix}-health-checker"
  arn       = aws_lambda_function.health_checker.arn
}

resource "aws_lambda_permission" "allow_eventbridge_health_check" {
  statement_id  = "AllowEventBridgeHealthCheckExecution"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health_checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.health_check_schedule.arn
}