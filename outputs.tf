
output "cloudops_status_table_name" {
  description = "Name of the DynamoDB table used by the CloudOps Incident Dashboard."
  value       = aws_dynamodb_table.cloudops_status.name
}

output "cloudops_status_table_arn" {
  description = "ARN of the DynamoDB table used by the CloudOps Incident Dashboard."
  value       = aws_dynamodb_table.cloudops_status.arn
}