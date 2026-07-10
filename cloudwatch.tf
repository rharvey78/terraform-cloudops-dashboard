
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