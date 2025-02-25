import os
import boto3
from botocore.exceptions import ClientError
import token_dispenser.configuration as configuration
# Initialize the DynamoDB resource
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv('DYNAMO_DB_CACHE_TABLE_NAME'))


def get_token_by_client_id(client_id:str):
    """
    Retrieves the token structure for the given client ID.

    Args:
        client_id: The unique identifier for the client.

    Returns:
        The token structure as a string, or None if no record is found.
    """
    try:
        response = table.get_item(Key={"client_id": client_id})
        return response.get("Item", {}).get("token_structure")
    except ClientError as e:
        print(f"Error fetching token: {e.response['Error']['Message']}")
        return None


def put_token(client_id:str, token_structure, ttl=None):
    """
    Inserts or updates a token in the DynamoDB table.

    Args:
        client_id: The unique identifier for the client.
        token_structure: The token structure as a string.
        ttl: Time to live in seconds (optional).
    """
    item = {
        "client_id": client_id,
        "token_structure": token_structure,
    }
    if ttl is not None:
        item["time_to_live"] = ttl

    try:
        table.put_item(Item=item)
    except ClientError as e:
        print(f"Error saving token: {e.response['Error']['Message']}")