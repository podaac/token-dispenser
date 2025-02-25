import boto3
import os
import logging
from token_dispenser.logging_config import shared_logger
# Initialize the S3 client
s3 = boto3.client('s3')

def download_s3_file(bucket_name: str, key: str, local_storage_dir: str) ->str:
    """
    Download a file from an S3 bucket to a local directory.

    :param bucket_name: Name of the S3 bucket
    :param key: Key of the file in the S3 bucket
    :param local_storage_dir: Local directory to save the downloaded file
    """
    log_adapter = shared_logger()
    log_adapter.info('Downloading file from S3 bucket %s', bucket_name)
    os.makedirs(local_storage_dir, exist_ok=True)

    # Extract the filename from the key
    filename = os.path.basename(key)

    # Full path to save the file locally
    local_file_path = os.path.join(local_storage_dir, filename)

    try:
        logging.info(f"downloading file from s3:{bucket_name} key:{key} to local_file:{local_file_path}")
        s3.download_file(bucket_name, key, local_file_path)

        # use print instead of TokenDispenserLogger because this is a very basic operation
        logging.info(f"File downloaded successfully to {local_file_path}")
        return local_file_path
    except Exception as e:
        # use print instead of TokenDispenserLogger because this is a very basic operation
        logging.error(f"Error downloading file: {e}")
        raise e