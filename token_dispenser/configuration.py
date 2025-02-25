import os

DEFAULT_LAUNCHPAD_GETTOKEN_URL:str =  "https://api.launchpad.nasa.gov/icam/api/sm/v1/gettoken"

# Launchpad token api url
LAUNCHPAD_GETTOKEN_URL: str = os.getenv('LAUNCHPAD_GETTOKEN_URL', DEFAULT_LAUNCHPAD_GETTOKEN_URL)
# The secret-id point to the Launchpad pfx password
LAUNCHPAD_PFX_PASSWORD_SECRET_ARN:str = os.getenv('LAUNCHPAD_PFX_PASSWORD_SECRET_ARN', '')
# The bucket will launchpad.pfx is stored. Ex. my-sndbx-bucket
LAUNCHPAD_PFX_FILE_S3_BUCKET = os.environ.get('LAUNCHPAD_PFX_FILE_S3_BUCKET')
# The key to point to launchpad.pfx Ex. /folder1/folder2/launchpad.pfx
LAUNCHPAD_PFX_FILE_S3_KEY = os.environ.get('LAUNCHPAD_PFX_FILE_S3_KEY')
# DynamoDB is used for cache clientId and token. If not passed in , the program shall fail
DYNAMO_DB_CACHE_TABLE_NAME: str = os.getenv('DYNAMO_DB_CACHE_TABLE_NAME')
# The os.getenv('AWS_REGION') should get the lambda's running region
AWS_REGION:str = os.getenv('AWS_REGION', 'us-west-2')
# lambda logging level
LOG_LEVEL:str = os.getenv('LOG_LEVEL','DEBUG')

# Default max token session timeout is 3600.  This value will be refreshed after acquiring new token
SESSION_MAXTIMEOUT:int = 3600
# Default value for token alive time in seconds. If token alive time is shorter than this value, then refresh before return
DEFAULT_TOKEN_MIN_ALIVE_SECS:int = 300
MINIMUM_ALIVE_SECS:int = int(os.getenv('MINIMUM_ALIVE_SECS', DEFAULT_TOKEN_MIN_ALIVE_SECS))
# Maximum value of client requested minimum_alive_secs.
# If client requesting minimum_alive_secs too close to 3600 secs, it will cause the program to refresh token too
# frequently which defeats the purpose of token cache.
MAX_REQUESTED_ALIVE_SECS:int = SESSION_MAXTIMEOUT - MINIMUM_ALIVE_SECS