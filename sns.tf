
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