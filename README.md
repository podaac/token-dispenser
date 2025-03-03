# launchpad-token-dispenser
    This project aims to create a centralized Token Dispenser Service (TDS) lambda function. Any application requiring access to 
a launchpad token can call this lambda with input parameters and receive a response containing the launchpad token, 
its creation time, and expiration time (all in EPOCH format).

# Security concerns, logging strategies
For security auditing, CloudTrail is recommended: https://docs.aws.amazon.com/lambda/latest/dg/logging-using-cloudtrail.html 

Two separate logs are advised:

* Security Auditing (CloudTrail): Captures security-related events.
* Application Usage Logging (CloudWatch + Client ID): Tracks application usage data.

Within the CloudWatch log, the lambda context will be logged. Here, the aws_request_id field can be used for
cross-referencing with CloudTrail logs. CloudTrail logs contain a requestId field that corresponds to the 
aws_request_id in the Lambda context.

While CloudTrail can be tied back to CloudWatch for setting up alarms, this is primarily useful for specific scenarios.
https://docs.aws.amazon.com/awscloudtrail/latest/userguide/monitor-cloudtrail-log-files-with-cloudwatch-logs.html?icmpid=docs_cloudtrail_console

# Functionality

## client_id and minimum_alive_secs
This project deploys a Launchpad Token Dispenser Service (TDS) lambda accessible through two parameters:

* client_id: Required field, alphanumeric type (English letters and numbers only). Hyphens (-) are not allowed, 
as they will cause input validation errors (e.g., "myID-123" will fail). IN more details, the program is validating
the input with regrex : re.compile(r'^[a-zA-Z0-9]{3,32}$')  minimum 3 , max 32 characters
* minimum_alive_secs (Optional): Numeric field (integer or long without decimals).

The client_id field allows the TDS lambda to cache tokens. When a subsequent request arrives with the same client_id, 
the TDS lambda attempts to retrieve the cached token value from its persistent layer (DynamoDB).
    
Example of Cached Token JSON Structure (all times in Unix EPOCH format):
```aiignore
{
  "authlevel" : 25,
  "cookiename" : "SMSESSION",
  "session_idletimeout" : 3600,
  "session_maxtimeout" : 3600,
  "sm_token" : "EJ3waHZVwqBOtrZkCl9PqxwShxWnlTeg==",
  "ssozone" : "SM",
  "status" : "success",
  "upn" : "svgspodaac@ndc.nasa.gov",
  "userdn" : "CN=svgspodaac,OU=Services,OU=Administrators,DC=ndc,DC=nasa,DC=gov",
  "expires_at": 173500,
  "created_at": 169900
}

```
The minimum_alive_secs field is used by the TDS lambda to verify if the difference between expires_at and the current time 
is greater than minimum_alive_secs. If true, the cached token is returned. Otherwise, a new token is generated, 
sent to the requester, and the cache is refreshed.

Sample Lambda Request: 

```aiignore
  Sample lambda request below:
  PAYLOAD=$(echo '{"client_id": "davidyen", "minimum_alive_secs": 120}' | base64)
  aws lambda invoke \
    --function-name sndbx-launchpad_token_dispenser \
    --payload "$PAYLOAD" \
    output.json
```
A successful response will contain a sample token JSON structure in output.json.

By design, each venue should run its own launchpad dispenser lambda to dispense operations, UAT, SIT, or sandbox launchpad tokens.

If minimum_alive_secs is not provided in the request, a cached token will be returned as long as it's not expired. 
Since launchpad tokens expire after 3600 seconds (1 hour), setting minimum_alive_secs close to 0 will cause 
frequent token refreshes, potentially overloading the launchpad application.

# 
#  Installation
The installation steps involved
* Downloading the lambda artifact and placing it under the $PROJECT_ROOT/dist directory.
* Creating a tfvars file or using `TF_VAR`
* Place launchpad.pfx file on s3 bucket
* Setup launchpad.pfx passphrase on secretmanager
* Terraform apply to deploy the project

## Download lambda artifact
The lambda artifact can be downloaded from the release page of this project.

Note: While build instructions are provided, building the lambda function locally can be complex due to the project's 
reliance on the cryptography library. This library requires platform-specific compilation of native extensions (.so files).

To simplify deployment and ensure compatibility, it is strongly recommended to use the pre-built artifact from the release page.

## Variables 
* Terraform Compatibility
This project has been tested with Terraform 1.10.4. Versions above 1.5.3 are expected to be compatible, 
while versions below 1.5.3 are not officially supported.

* TFVars Variables
This section outlines the necessary Terraform variables. Users can manage these variables by:
**Creating a prefix.tfvars file.
**Utilizing environment variables in the format TF_VAR_<variable_name>.

| config key                                 | description                                                                                                                         |
|--------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `prefix`                                   | prefix of lambda. If intent to deploy one TDS per env, suggested to set it as sndbx/sit/uat or ops based on the running environment |
| `credentials`                              | full path of credential file. Ex. /User/Mynam/.aws/credentials                                                                      |
| `profile`                                  | Name of the AWS profile from the credentials file                                                                                   |
| `log_retention_days`                       | Number of days where TDS lambda will be retained                                                                                    |
| `permissions_boundary_arn`                 | Lambda permission boundary ARN                                                                                                      |
| `launchpad_gettoken_url`                   | Launchpad application /gettoken URL                                                                                                 |
| `launchpad_pfx_passcode_secret_arn`        | the ARN of the secret where launchpad pfx password is stored.                                                                       |
| `launchpad_pfx_file_s3_bucket`             | S3 bucket where launchpad.pfx file is stored. Ex. my-internal-bucket                                                                |
| `launchpad_pfx_file_s3_key`                | S3 key where launchpad.pfx file is stored. Ex. my-prefix/crypto/launchpad.pfx                                                       |
| `launchpad_token_dispenser_lambda_timeout` | TDS lambda timeout                                                                                                                  |
| `minimum_alive_secs`                       | if client passed in minimum_alive_secs greater than this, than error out                                                            |
| `client_expiration_secon`                  | A number of seconds when a client's (based on client_id) cached token is permanently purged from dynamoDB                           |

## Place launchpad.pfx file on s3 bucket
This document does not cover the specifics of launchpad token management, such as how to obtain or manage launchpad.pfx certificates.

- Launchpad.pfx Management:
 -Obtain Launchpad.pfx:
  - Launchpad.pfx certificates are typically associated with a user's EarthData User ID.
  - Obtain the certificate through the appropriate channels within your organization (e.g., through the Network Access Management System (NAMS)).

-Storage:
 -Once obtained, download the launchpad.pfx file and store it securely in an S3 bucket.
 -Configure the launchpad_pfx_file_s3_bucket and launchpad_pfx_file_s3_key variables in your tfvars file to reflect the S3 bucket and key where the launchpad.pfx file is stored.

## Setup launchpad.pfx passphrase on secretmanager

* create secret before put-secret-value to update:
```aiignore
aws secretsmanager create-secret \
     --name mysecrete1 \
    --description "A test secret for storing user credentials" \
    --secret-string "launchpad-pfx-passpphrase" \
    --profile my-aws-profile
    
```
* use put-secret-value to write secret value AFTER secret has been created
```aiignore
aws secretsmanager put-secret-value \
     --secret-id mysecrete1 \
     --secret-string "launchpad-pfx-passpphrase"" \
      --profile my-aws-profile
```
In the example above, the launchpad_pfx_password_secret_id variable should be set to mysecrete1.

To obtain the launchpad_pfx_password_secret_arn, navigate to the Secrets Manager service in the AWS console.
Locate the "mysecrete1" secret and retrieve its ARN.

Set this ARN to the launchpad_pfx_password_secret_arn variable in your tfvars file.

This configuration grants the TDS the necessary permissions to read only the secret containing the launchpad.pfx passphrase.

Reference documents:
generic document : https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/put-secret-value.html
document with example : https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_update-secret-value.html

## Terraform based Deployment
To deploy this project using Terraform, follow these steps:
* Configure the venue.tf file: This file specifies the location of your Terraform state file (tfstate). Update the configuration within venue.tf to reflect the desired location (e.g., S3 bucket, local filesystem).
* Download lambda build artifact
* Create the venue.tfvars file: This file defines the Terraform variables required for deployment. Populate this file with the values mentioned in the [## Variables] section of this document.
* Execute Terraform commands: Once the configuration files are set up, use the Terraform CLI to execute the deployment process. Refer to the Terraform documentation for specific commands (e.g., terraform init, terraform plan, terraform apply).

### Configure tfstate file
The $PROJECT_ROOT/backend directory contains sample venue.tf files being used to configure where the TDS project's tfstate file will be located.
Ex.
```aiignore
bucket         = "my-cumulus-tf-state"
key            = "launchpad-token-dispenser/sndbx/terraform.tfstate"
region         = "us-west-2"
```
Please decide where the tfstate file will be located and configure venue.tf file acoordingly before moving forward. It is up to the user
to decide to use local location, S3 or terraform cloud to store tfstate file.

## Download and setup build artifact
Download build artifact from release page, rename it to token-dispenser_lambda.zip and place it under 
 $PROJECT_ROOT/dist/token-dispenser_lambda.zip

## Configure tfvars file
Example:
```aiignore
prefix = "sndbx"
log_retention_days = 14
permissions_boundary_arn ="arn:aws:iam::06xxxxxxxxx:policy/XXXXXRoleBoundary"
launchpad_pfx_passcode_secret_arn = "arn:aws:secretsmanager:us-west-2:06xxxxxxxxx:secret:prefix-message-template-launchpad-passphrase0000000000000-SolCpg"
# The bucket where launchpad.pfx is stored. Ex. my-sndbx-bucket
launchpad_pfx_file_s3_bucket="my-bucket-internal"
# The key to point to launchpad.pfx Ex. /folder1/folder2/launchpad.pfx
launchpad_pfx_file_s3_key="my-prefix/crypto/launchpad.pfx"
```

## Terraform based Deployment Command Examples
Assuming build artifact is downloaded and placed in $PROJECT_ROOT/dist/token-dispenser_lambda.zip
Tested with Terraform release 1.10.4. Example below assumes terraform executable file is named terraform
```aiignore
export AWS_SHARED_CREDENTIALS_FILE=~/.aws/credentials
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-west-2
terraform init --backend-config=backends/sndbx.tf -reconfigure -backend-config="profile=my-profile"
terraform plan -var-file=tfvars/sndbx.tfvars -var="credentials=~/.aws/credentials" -var="profile=my-profile"
terraform apply -var-file=tfvars/sndbx.tfvars -auto-approve -var="credentials=~/.aws/credentials" -var="profile=my-profile"
```

# Build software
build lambda through amazon python 3.12-x86_64 image which is based on linux 3
```aiignore
docker pull public.ecr.aws/lambda/python:3.12-x86_64
# example : docker run --rm --name java-python -it podaac-java-python:latest bash
docker run --rm --name python312 -v /tmp:/tmp -it public.ecr.aws/lambda/python:3.12-x86_64 bash
# To run amazon ecr based image.  use --entrypoint to overwrite the entry point
docker run --rm --name python312 -v /tmp/mydir:/tmp/mydir -it --entrypoint bash public.ecr.aws/lambda/python:3.12-x86_64

curl -sSL https://install.python-poetry.org | python3 - --version 2.0.0
export PATH=/root/.local/bin:$PATH
pwd;mkdir venv;mkdir -p build/lambda;mkdir -p build/dist
poetry config virtualenvs.path venv
poetry lock
poetry install
cp -R token_dispenser venv/*/lib/*/site-packages/
chmod -R 775 venv/*/lib/*/site-packages/
cd env/*/lib/*/site-packages/; zip -r ../artifact.zip .
```
