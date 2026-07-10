
output "cloudops_status_table_name" {
  description = "Name of the DynamoDB table used by the CloudOps Incident Dashboard."
  value       = aws_dynamodb_table.cloudops_status.name
}

output "cloudops_status_table_arn" {
  description = "ARN of the DynamoDB table used by the CloudOps Incident Dashboard."
  value       = aws_dynamodb_table.cloudops_status.arn
}


# ============================================================
# Public Status API endpoint
#
# Returns the full URL used by the dashboard frontend to retrieve
# the latest workload health status records.
# ============================================================

output "cloudops_status_api_url" {
  description = "Public URL for the CloudOps dashboard status API."
  value       = "${aws_apigatewayv2_api.cloudops_api.api_endpoint}/status"
}