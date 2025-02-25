data "aws_iam_policy_document" "launchpad_token_dispenser_lambda_assume_role_policy" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "launchpad_token_dispenser_lambda_role" {
  name                 = "${local.prefix}_launchpad_token_dispenser_lambda_processing"
  assume_role_policy   = data.aws_iam_policy_document.launchpad_token_dispenser_lambda_assume_role_policy.json
  permissions_boundary = "arn:aws:iam::${local.account_id}:policy/NGAPShRoleBoundary"
}

data "aws_iam_policy_document" "launchpad_token_dispenser_lambda_processing_policy" {

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    # resources = [aws_cloudwatch_log_group.launchpad_token_dispenser_lambda_log_group.arn ]
    resources = [
      aws_cloudwatch_log_group.launchpad_token_dispenser_lambda_log_group.arn,
    "${aws_cloudwatch_log_group.launchpad_token_dispenser_lambda_log_group.arn}:*"
    ]
  }

  statement {
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:UpdateContinuousBackups",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:Query"
    ]
    resources = [aws_dynamodb_table.launchpad_token_dispenser_cache_table.arn]
  }

  statement {
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:CreateTable"
    ]
    resources = ["*"]
  }

  statement {
    actions   = ["dynamodb:Query"]
    resources = ["${aws_dynamodb_table.launchpad_token_dispenser_cache_table.arn}/index/*"]
  }

  statement {
    actions = [
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams"
    ]
    resources = ["${aws_dynamodb_table.launchpad_token_dispenser_cache_table.arn}/stream/*"]
  }

  statement {
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      var.launchpad_pfx_passcode_secret_arn
    ]
  }

  statement {
    sid       = "AllowReadAccessToLaunchpadPfxBucket"
    actions   = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.launchpad_pfx_file_s3_bucket}",
      "arn:aws:s3:::${var.launchpad_pfx_file_s3_bucket}/*"
    ]
  }
}

# This role policy resource is to "glue" the iam role with a policy
 resource "aws_iam_role_policy" "launchpad_token_dispenser_lambda_processing" {
  name   = "${local.prefix}_launchpad_token_dispenser_lambda_processing_policy"
  role   = aws_iam_role.launchpad_token_dispenser_lambda_role.id
  policy = data.aws_iam_policy_document.launchpad_token_dispenser_lambda_processing_policy.json
}