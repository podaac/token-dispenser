
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from token_dispenser.logging_config import shared_logger
# Create a Secrets Manager client
client = boto3.client('secretsmanager')


def get_secret_value(secret_id_or_arn: str) -> str:
    """
    Retrieves the secret value for the given secret_id or secret_id's ARN from AWS Secrets Manager.

    Args:
        secret_id_or_arn (str): The identifier of the secret.

    Returns:
        str: The value of the secret as a string.

    Raises:
        Exception: If the secret cannot be retrieved.
    """
    logger = shared_logger()
    try:
        logger.debug('Retrieving secret value from AWS Secrets Manager.')
        # Retrieve the secret value
        response = client.get_secret_value(SecretId=secret_id_or_arn)
        # Check if the secret is stored as a string
        if 'SecretString' in response:
            logger.debug('Retrieved pkcs12 secret value from AWS Secrets Manager successfully.')
            return response['SecretString']
        else:
            # Handle binary secrets if necessary
            raise ValueError("Secret is stored in binary format, not supported in this implementation.")
    except (BotoCoreError, ClientError) as error:
        # Handle errors from Secrets Manager
        logger.exception(f'Error retrieving secret {secret_id_or_arn}: {error}')
        raise Exception(f"Error retrieving secret {secret_id_or_arn}: {error}")
