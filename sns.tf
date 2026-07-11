
# ============================================================
# CloudOps alert notification topic
#
# CloudWatch alarms will publish alert notifications to this
# SNS topic. Subscribers, such as email addresses, can then
# receive those operational alerts.
# ============================================================

resource "aws_sns_topic" "cloudops_alerts" {
  name = "${local.name_prefix}-alerts"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alerts"
  })
}


# ============================================================
# Email subscription for CloudOps alerts
#
# Subscribes the email address stored in the Terraform variable
# alert_email to the CloudOps SNS alert topic.
#
# AWS will send a confirmation email. Alerts will not be
# delivered until the subscription is confirmed.
# ============================================================

resource "aws_sns_topic_subscription" "cloudops_alert_email" {
  topic_arn = aws_sns_topic.cloudops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}