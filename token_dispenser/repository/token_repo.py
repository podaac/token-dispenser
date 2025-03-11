"""
This module provides ability to read and write to token dispenser cache which is
AWS DynamoDB
"""
import os
import boto3
from botocore.exceptions import ClientError
from token_dispenser.logging_config import shared_logger
# Initialize the DynamoDB resource
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv('DYNAMO_DB_CACHE_TABLE_NAME'))


def get_token_by_client_id(client_id: str):
    """
    Retrieves the token structure for the given client ID.

    Args:
        client_id: The unique identifier for the client.

    Returns:
        The token structure as a string, or None if no record is found.
    """
    logger = shared_logger()
    try:
        response = table.get_item(Key={"client_id": client_id})
        return response.get("Item", {}).get("token")
    except ClientError as exception:
        logger.exception(f'Error fetching token {exception}')
        return None


def put_token(client_id: str, token, ttl):
    """
    Inserts or updates a token in the DynamoDB table.

    Args:
        client_id: The unique identifier for the client.
        token: The token structure as a string.
        ttl: Time to live in seconds (optional).
    """
    logger = shared_logger()
    item = {"client_id": client_id, "token": token, "time_to_live": ttl}

    try:
        table.put_item(Item=item)
    except ClientError as exception:
        logger.exception("Error saving token")
        raise exception
