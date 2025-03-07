variable "default_tags" {
  type = map(string)
  default = {}
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

# While client making request to the Token Dispenser Server (TDS) lambda, a client_id and minimum_alive_secs are
# passed in. If token is cached within dynamoDB and the token is expiring longer than the minimum_alive_secs, then
# just return the cached token. Otherwise, request new token and cache the newly obtained token to dynamoDB
# Developer could choose to overwrite this number but please be noted that if this number is too large (or too close to
# the current token alive time (which is 60 mins), than it will cause frequent token refresh
variable "minimum_alive_secs" {
  description = "The token must be alive at least minimum_alive_sec, otherwise get new token"
  type        = number
  default     = 300
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
variable "launchpad_pfx_file_s3_bucket"{
  type    = string
}


# The key to point to launchpad.pfx Ex. /folder1/folder2/launchpad.pfx
variable "launchpad_pfx_file_s3_key" {
  type    = string
}

# The ARN of the secret storing pfx passcode
variable "launchpad_pfx_passcode_secret_arn" {
  type    = string
}
