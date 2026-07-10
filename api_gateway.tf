
# ============================================================
# API Gateway HTTP API
#
# This public API provides the dashboard frontend with access
# to the latest workload health data returned by the Status API
# Lambda function.
# ============================================================

resource "aws_apigatewayv2_api" "cloudops_api" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api"
  })
}