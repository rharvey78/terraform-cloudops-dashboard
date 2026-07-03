
variable "aws_region" {
  description = "AWS region for all CloudOps Incident Dashboard resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for AWS resource naming."
  type        = string
  default     = "cloudops-incident-dashboard"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "demo"
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs."
  type        = number
  default     = 7
}

variable "health_check_schedule" {
  description = "EventBridge schedule expression for health checks."
  type        = string
  default     = "rate(1 hour)"
}

variable "alert_email" {
  description = "Email address for CloudOps alert notifications."
  type        = string
  default     = "ron.harvey2020@gmail.com"
}

variable "health_check_timeout_seconds" {
  description = "Timeout in seconds for each individual workload health check."
  type        = number
  default     = 10
}

variable "workloads" {
  description = "List of workload endpoints checked by the CloudOps health checker Lambda."
  type = list(object({
    name            = string
    url             = string
    expected_status = optional(number, 200)
    runbook_url     = optional(string, "")
  }))
  default = []
}