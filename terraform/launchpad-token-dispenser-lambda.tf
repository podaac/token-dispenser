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

resource "aws_cloudwatch_log_group" "tds_cloudtrail_log_group" {
  name              = "/aws/cloudtrail/${var.prefix}-launchpad-token-dispenser"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "tds_cloudtrail_to_cloudwatch_role" {
  name = "${var.prefix}-cloudtrail-to-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Inline IAM Policy for CloudTrail to write to CloudWatch Logs
resource "aws_iam_role_policy" "tds_cloudtrail_to_cloudwatch_policy" {
  name = "${var.prefix}-cloudtrail-to-cloudwatch-policy"
  role = aws_iam_role.tds_cloudtrail_to_cloudwatch_role.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "${aws_cloudwatch_log_group.tds_cloudtrail_log_group.arn}:*"
        ]
      }
    ]
  })
}

resource "aws_cloudtrail" "launchpad_token_dispenser_trail" {
  name                          = "${var.prefix}-launchpad-token-dispenser-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail_bucket.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                = true

  # Bind cloudtrail to the CloudWatch Logs group
  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.tds_cloudtrail_log_group.arn}:*"
  cloud_watch_logs_role_arn  = aws_iam_role.tds_cloudtrail_to_cloudwatch_role.arn


  event_selector {
    read_write_type           = "All"
    include_management_events = false
    data_resource {
      type   = "AWS::Lambda::Function"
      values = [aws_lambda_function.launchpad_token_dispenser_lambda.arn]
    }
  }
}

# Generate a random string to ensure bucket name uniqueness
resource "random_string" "cloudtrail_bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# S3 bucket for CloudTrail logs
resource "aws_s3_bucket" "cloudtrail_bucket" {
  bucket = "${var.prefix}-cloudtrail-logs-${random_string.cloudtrail_bucket_suffix.result}"

  lifecycle {
    prevent_destroy = false
  }

  # Add lifecycle rule to expire objects after 7 days
  lifecycle_rule {
    id      = "delete-cloudtrail-logs"
    enabled = true

    expiration {
      days = 7
    }
  }
}

# S3 bucket policy for CloudTrail
resource "aws_s3_bucket_policy" "tds_cloudtrail_bucket_policy" {
  bucket = aws_s3_bucket.cloudtrail_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid = "TDSCloudTrailGetBucketAcl",
        Effect = "Allow",
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        },
        Action = "s3:GetBucketAcl",
        Resource = "${aws_s3_bucket.cloudtrail_bucket.arn}"
      },
      {
        Sid = "TDSCloudTrailWrite",
        Effect = "Allow",
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        },
        Action = "s3:PutObject",
        Resource = "${aws_s3_bucket.cloudtrail_bucket.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*",
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}
