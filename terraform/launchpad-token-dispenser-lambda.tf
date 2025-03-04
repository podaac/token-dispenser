resource "aws_lambda_function" "launchpad_token_dispenser_lambda" {
  filename          = "../dist/token-dispenser_lambda.zip"
  function_name     = "${var.prefix}-launchpad_token_dispenser"
  role              = aws_iam_role.launchpad_token_dispenser_lambda_role.arn
  handler           = "token_dispenser.token_dispenser_lambda.handler"
  source_code_hash  = filebase64sha256("../dist/token-dispenser_lambda.zip")
  architectures     = ["x86_64"]
  runtime           = "python3.12"
  timeout           = var.launchpad_token_dispenser_lambda_timeout
  memory_size       = var.launchpad_token_dispenser_lambda_memory_size

  depends_on = [aws_cloudwatch_log_group.launchpad_token_dispenser_lambda_log_group]

  logging_config {
    log_group = aws_cloudwatch_log_group.launchpad_token_dispenser_lambda_log_group.name
    log_format = "Text"
  }

  environment {
    variables = {
      LAUNCHPAD_GETTOKEN_URL                  = var.launchpad_gettoken_url
      # minimum_alive_secs
      MINIMUM_ALIVE_SECS                      = var.minimum_alive_secs
      # The secret arn point to the Launchpad pfx password
      LAUNCHPAD_PFX_PASSWORD_SECRET_ARN       = var.launchpad_pfx_passcode_secret_arn
      # The bucket will launchpad.pfx is stored. Ex. my-sndbx-bucket
      LAUNCHPAD_PFX_FILE_S3_BUCKET            = var.launchpad_pfx_file_s3_bucket
      # The key to point to launchpad.pfx Ex. /folder1/folder2/launchpad.pfx
      LAUNCHPAD_PFX_FILE_S3_KEY               = var.launchpad_pfx_file_s3_key
      # DynamoDB cache table name
      DYNAMO_DB_CACHE_TABLE_NAME              = aws_dynamodb_table.launchpad_token_dispenser_cache_table.name
      # LOG LEVEL
      LOG_LEVEL                               = var.log_level
    }
  }
}

resource "aws_cloudwatch_log_group" "launchpad_token_dispenser_lambda_log_group" {
  name              = "/aws/lambda/${var.prefix}-launchpad_token_dispenser"
  retention_in_days = var.log_retention_days
}

# write the created lambda function ARN into ssm under /service/token-dispenser/${prefix}
resource "aws_ssm_parameter" "launchpad_token_dispenser_lambda_arn" {
  name  = "/service/token-dispenser/${var.prefix}"
  type  = "String"
  value = aws_lambda_function.launchpad_token_dispenser_lambda.arn
}