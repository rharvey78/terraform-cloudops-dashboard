
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


# ============================================================
# API Gateway integration with the Status API Lambda
#
# This connects the HTTP API to the Status API Lambda using
# Lambda proxy integration. Requests sent through API Gateway
# will be passed directly to the Lambda function.
# ============================================================

resource "aws_apigatewayv2_integration" "status_api_lambda" {
  api_id = aws_apigatewayv2_api.cloudops_api.id

  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.status_api.invoke_arn

  payload_format_version = "2.0"
}


# ============================================================
# GET /status route
#
# This route maps HTTP GET requests for /status to the
# Status API Lambda integration defined above.
# ============================================================

resource "aws_apigatewayv2_route" "status" {
  api_id = aws_apigatewayv2_api.cloudops_api.id

  # Public HTTP route used by the dashboard frontend.
  route_key = "GET /status"

  # Send matching requests to the Status API Lambda integration.
  target = "integrations/${aws_apigatewayv2_integration.status_api_lambda.id}"
}