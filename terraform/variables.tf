variable "default_tags" {
  type = map(string)
  default = {}
}


##################################################################
# The arn of response sns where CNMResponse lambda shall publish
# messages into
##################################################################

variable "credentials" {
  default = "~/.aws/credentials"
}

# AWS profile name
variable "profile" {
  type = string
}

# sndbx, sit, uat, ops or any user defined prefix
variable "prefix" {
  type = string
}

# Usually configured as DAAC name.  ex. PODAAC_IandA
variable "team" {
  type = string
}

# Launchpad Token Dispensing Lambada timeout in secs
variable "launchpad_token_dispenser_lambda_timeout" {
  type    = number
  default = 20
}

variable "launchpad_token_dispenser_lambda_memory_size" {
  type    = number
  default = 128
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "log_level" {
  description = "The log level to be used."
  type        = string

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "The log level must be one of 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'."
  }

  default = "INFO"
}

variable "launchpad_gettoken_url" {
  type    = string
  default = "https://api.launchpad.nasa.gov/icam/api/sm/v1/gettoken"
}

# The bucket where launchpad.pfx is stored. Ex. my-sndbx-bucket
variable "launchpad_pfx_file_s3_bucket"{}

# The key to point to launchpad.pfx Ex. /folder1/folder2/launchpad.pfx
variable "launchpad_pfx_file_s3_key" {}

# The ARN of the secret storing pfx passcode
variable "launchpad_pfx_passcode_secret_arn" {}

# DynamoDB configuration
# the requester for token dispenser lambda will provide a client_id as input.  By using the client_id,
# token is cached in dynamoDB.  This value indicates
# how long the client_id entry will be kept before deletion, in unix EPOCH format. default = 3 days
variable "client_expiration_seconds" {
  type    = number
  default = 259200
}
