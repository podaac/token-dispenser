"""
import some dummy env variables for unit tests to run
"""
import os

os.environ['AWS_REGION'] = 'us-west-2'
os.environ['DYNAMO_DB_CACHE_TABLE_NAME'] = 'sndbx-LaunchpadTokenDispenserCacheTable'
os.environ['LAUNCHPAD_PFX_FILE_S3_BUCKET'] = 'sndbx-myBucket'
os.environ['LAUNCHPAD_PFX_FILE_S3_KEY'] = 'pfx-Key'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['LAUNCHPAD_PFX_PASSWORD_SECRET_ARN'] = 'aws:arn:xxxxxx'
