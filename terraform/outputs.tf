# Output the Token Dispenser ARN. Being useful for pulling remote state
output "token_dispenser_lambda_arn" {
  value = aws_lambda_function.launchpad_token_dispenser_lambda.arn
}