
resource "aws_dynamodb_table" "cloudops_status" {
  name         = "${local.name_prefix}-status"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "pk"
  range_key = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  # The table stores only the latest operational status for each workload,
  # so record expiration is not required. Keep TTL explicitly disabled.
  ttl {
    enabled = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status"
  })
}
