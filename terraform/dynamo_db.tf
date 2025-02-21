resource "aws_dynamodb_table" "launchpad_token_dispenser_cache_table" {
  name           = "${var.prefix}-LaunchpadTokenDispenserCacheTable"           # Name of the DynamoDB table
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "client_id"                                # On-demand billing mode (no need to specify capacity)

  # Define the schema for the table (the "id" attribute as a string)
  attribute {
    name = "client_id"
    type = "S"  # String type
  }

  ttl {
    attribute_name = "time_to_live"
    enabled        = true
  }

  tags = local.default_tags
}