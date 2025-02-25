from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.backends import default_backend

from token_dispenser.aws.s3 import download_s3_file
from token_dispenser.aws.secret_manager import get_secret_value
from token_dispenser.aws.launchpad_token import get_token
import token_dispenser.configuration as config
from token_dispenser.repository.token_repo import put_token, get_token_by_client_id
import json, re
import logging
from token_dispenser.logging_config import initialize_logger, shared_logger
import time

def decode_pkcs12(p12_file_path, password: str):
    """
    Decodes a PKCS#12 file to extract the private key, certificate, and additional certificates.

    :param p12_file_path: Path to the PKCS#12 file (.p12 or .pfx).
    :param password: Password for the PKCS#12 file (if any).
    :return: A tuple containing the private key, certificate, and additional certificates.
    """
    with open(p12_file_path, "rb") as file:
        pkcs12_data = file.read()

    # Decode the PKCS#12 file
    private_key, certificate, additional_certs = load_key_and_certificates(
        pkcs12_data,
        password.encode("utf-8") if password else None,
        backend=default_backend()
    )
    return private_key, certificate, additional_certs


def get_new_token(client_id:str):
    """
    obtain a new token based on client_id and write the newly obtained token into DynamoDB

    :param client_id: a required field which is used as key to cache the token in dynamoDB.
    :return: a json object containing the token data.
    """
    try:
        p12_file = download_s3_file(bucket_name=config.LAUNCHPAD_PFX_FILE_S3_BUCKET,
                                            key=config.LAUNCHPAD_PFX_FILE_S3_KEY, local_storage_dir='/tmp')
        shared_logger().info(f"p12 file downloaded from s3 successfully to: {p12_file}")
        password = get_secret_value(config.LAUNCHPAD_PFX_PASSWORD_SECRET_ARN)
        private_key, cert, additional_certs = decode_pkcs12(p12_file, password)
        shared_logger().info(f"cert files decoded successfully")
        # Create launchpad token
        token_json = get_token(url=config.LAUNCHPAD_GETTOKEN_URL, private_key=private_key,
                                                        certificate=cert)
        put_token(client_id, json.dumps(token_json), int(token_json['expires_at']))
        return token_json
    except Exception as e:
        print(f"Failed on get_new_token process: {e}")
        raise e


def satisfy_minimum_alive_secs(token_json:json, minimum_alive_secs:int) -> bool:
    # if the minimum_alive_sec is not provided by requester or value less than 0
    # it means the request does not care so we will assume whatever cached is ok
    if minimum_alive_secs is None or minimum_alive_secs <= 0:
        return True
    expires_at = int(token_json.get('expires_at'))
    if expires_at - time.time() > minimum_alive_secs:
        return True
    else:
        return False

def is_client_id_valid(client_id:str|None) -> bool:
    pattern = re.compile(r'^[a-zA-Z0-9]{3,32}$')
    if pattern.match(client_id):
        return True
    else:
        return False


def is_minimum_alive_secs_valid(minimum_alive_secs:int or None) -> bool :
    if minimum_alive_secs is not None and (not minimum_alive_secs.is_integer()):
        return False

    if ((minimum_alive_secs is not None and minimum_alive_secs.is_integer()) and
            (minimum_alive_secs > config.MAX_REQUESTED_ALIVE_SECS or minimum_alive_secs < 0)):
        return False
    else:
        return True


def handler(event, context):
    print(event)
    print('region-region: {}'.format(config.AWS_REGION))
    client_id = event.get('client_id', '')
    print("client_id: {client_id}")
    minimum_alive_secs: int|None= int(event.get('minimum_alive_secs', config.DEFAULT_TOKEN_MIN_ALIVE_SECS))
    # client_id must be alphanumeric
    if not is_client_id_valid(client_id):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "client_id is required in request. Must be alpha-numeric"})
        }
    if not is_minimum_alive_secs_valid(minimum_alive_secs):
        return {
            "statusCode": 422,
            "body": json.dumps({"error": f"minimum_alive_secs if provided, must be numeric "
                                         f"and smaller or equal than {config.MAX_REQUESTED_ALIVE_SECS} secs"})
        }
    # Set the logging level dynamically
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    print(f"log_level: {log_level}")
    # Reconfigure the logger with the new log level
    log_adapter = initialize_logger(log_level, client_id=client_id)
    # This lambda does not burden user with required minimum_alive_sec. If such field is not provided by the caller
    # it will be set to the default value.
    if minimum_alive_secs is None:
        log_adapter.info(f"client passed in empty minimum_alive_secs, using default value as:"
                         f" {config.DEFAULT_TOKEN_MIN_ALIVE_SECS}")
        minimum_alive_secs = config.DEFAULT_TOKEN_MIN_ALIVE_SECS
    # if the token expected to be expired shorter than the expiration time, then
    # get a new token, save new token to dynamoDB with new TTL
    # minimum_alive_secs:int|None = int(json.loads(event['body'])['minimum_alive_secs'])
    log_adapter.info(f"client_id with context: {context}")
    log_adapter.info(f"dynamoDB region: {config.AWS_REGION}")
    log_adapter.info(f"dynamoDB table name: {config.DYNAMO_DB_CACHE_TABLE_NAME}")
    log_adapter.info(f'client_id: {client_id}  minimum_alive_secs: {minimum_alive_secs}')

    token_json = None
    # Retrieve token structure from DynamoDB using client_id
    try:
        # When a request comes in, check dynamoDB first, if not found then get new token
        token_structure_str:str = get_token_by_client_id(client_id)
        if token_structure_str is not None:
            token_json = json.loads(token_structure_str)
        if token_structure_str is not None and satisfy_minimum_alive_secs(token_json, minimum_alive_secs):
            return token_structure_str
        else:
            # retrieve new token , save to dynamoDB and return new token
            token_json = get_new_token(client_id) # this function will retrieve new token and save it to cache
            return json.dumps(token_json)

    except Exception as e:
        log_adapter.error(f"Error processing client_token: {str(e)}")
        raise e