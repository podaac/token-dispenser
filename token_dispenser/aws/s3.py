"""
This module provides ability to download from s3 bucket
"""
import os
import boto3
from token_dispenser.logging_config import shared_logger
# Initialize the S3 client
s3 = boto3.client('s3')


def download_s3_file(bucket_name: str, key: str, local_storage_dir: str) -> str:
    """
    Download a file from an S3 bucket to a local directory.

    :param bucket_name: Name of the S3 bucket
    :param key: Key of the file in the S3 bucket
    :param local_storage_dir: Local directory to save the downloaded file
    """
    logger = shared_logger()
    logger.info(f'Downloading file from S3 bucket {bucket_name}')
    os.makedirs(local_storage_dir, exist_ok=True)

    # Extract the filename from the key
    filename = os.path.basename(key)

    # Full path to save the file locally
    local_file_path = os.path.join(local_storage_dir, filename)

    try:
        logger.info(f"downloading file from s3:{bucket_name} key:{key} "
                    f"to local_file:{local_file_path}")
        s3.download_file(bucket_name, key, local_file_path)

        logger.info(f"File downloaded successfully to {local_file_path}")
        return local_file_path
    except Exception as exception:
        logger.exception("Error downloading file")
        raise exception
