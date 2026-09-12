
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

  # TTL remains configured to match the existing table state.
  # Current CloudOps status records do not write the expires_at attribute,
  # so no records are automatically expired by this setting.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-status"
  })
}
