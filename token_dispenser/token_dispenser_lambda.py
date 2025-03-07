from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from tempfile import NamedTemporaryFile
from token_dispenser.aws.s3 import download_s3_file
from token_dispenser.aws.secret_manager import get_secret_value
from token_dispenser.aws.launchpad_token import get_token
import token_dispenser.configuration as config
from token_dispenser.repository.token_repo import put_token, get_token_by_client_id
import os, json, re
import logging
from token_dispenser.logging_config import initialize_logger, shared_logger
import time

cached_cert_file:NamedTemporaryFile = None
# Set the logging level dynamically
log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)

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
        password.encode("utf-8"),
        backend=default_backend()
    )
    return private_key, certificate, additional_certs

def build_cached_cert_file(private_key, certificate):
    logger = shared_logger()
    global cached_cert_file
    try:
        logger.debug(f"entered build_cached_cert_file")
        # Serialize private key and certificate into PEM format
        private_key_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption()
        ).decode("utf-8")

        certificate_pem = certificate.public_bytes(Encoding.PEM).decode("utf-8")
        # Combine private key and certificate into a single file for mutual TLS authentication
        # The single file is managed by tempfile.NamedTemporaryFile where the library creates an arbitrary file
        # and be responsible to remove the file while exiting the python virtual machine even if exception happened
        if cached_cert_file is None:
            cached_cert_file = NamedTemporaryFile(delete=True)  # Important: delete=True. deletion after python exits
            cached_cert_file.write(private_key_pem.encode('utf-8'))
            cached_cert_file.write(certificate_pem.encode('utf-8'))
            cached_cert_file.flush()
            logger.info('cached certificate pem and private combination created.')
        else:
            logger.info('cached certificate pem and private combination already exists.')
            cached_cert_file.seek(0)  # reset file pointer
        return cached_cert_file
    except Exception as e:
        logger.error(f"build_cached_cert_file error occurred: {str(e)}")
        raise e

def get_new_token(client_id:str):
    """
    obtain a new token based on client_id and write the newly obtained token into DynamoDB
    This function try to cache the cert file (a combination of private key and cert str). If the cached cert file exists,
     use the cached cert to get token.  Otherwise, go through pkc12 download, decode, build cert file and get token

    :param client_id: a required field which is used as key to cache the token in dynamoDB.
    :return: a json object containing the token data.
    """
    global cached_cert_file
    logger = shared_logger()
    try:
        if cached_cert_file is not None and os.path.exists(cached_cert_file.name) and os.path.getsize(cached_cert_file.name) >0:
            logger.debug(f"found cached cert file {cached_cert_file.name}")
            get_token(url=config.LAUNCHPAD_GETTOKEN_URL, cert_file=cached_cert_file.name)
        else:
            logger.debug(f"cached cert file not found")
            p12_file = download_s3_file(bucket_name=config.LAUNCHPAD_PFX_FILE_S3_BUCKET,
                                                key=config.LAUNCHPAD_PFX_FILE_S3_KEY, local_storage_dir='/tmp')
            logger.info(f"p12 file downloaded from s3 successfully to: {p12_file}")
            password = get_secret_value(config.LAUNCHPAD_PFX_PASSWORD_SECRET_ARN)
            private_key, cert, additional_certs = decode_pkcs12(p12_file, password)
            cached_cert_file = build_cached_cert_file(private_key, cert)
            # Create launchpad token
            token_json = get_token(url=config.LAUNCHPAD_GETTOKEN_URL, cert_file=cached_cert_file.name)
        put_token(client_id, json.dumps(token_json), int(token_json['expires_at']))
        return token_json
    except Exception as e:
        print(f"Failed on get_new_token process: {e}")
        raise e


def satisfy_minimum_alive_secs(expires_at:int, minimum_alive_secs:int) -> bool:
    # if the minimum_alive_sec is not provided by requester or value less than 0
    # it means the request does not care so we will assume whatever cached is ok
    if minimum_alive_secs is None or minimum_alive_secs <= 0:
        return True
    if expires_at - time.time() > minimum_alive_secs:
        return True
    else:
        return False

def is_client_id_valid(client_id:str) -> bool:
    pattern = re.compile(r'^[a-zA-Z0-9]{3,32}$')
    return bool(pattern.match(client_id))


def is_minimum_alive_secs_valid(minimum_alive_secs:int) -> bool :
    # If reached this point, minimum_alive_secs can not be NONE
    if not isinstance(minimum_alive_secs, int):
        return False

    if  (isinstance(minimum_alive_secs, int) and
            minimum_alive_secs > config.MAX_REQUESTED_ALIVE_SECS or minimum_alive_secs < 0):
        return False
    else:
        return True


def handler(event, context):
    client_id = event.get('client_id')
    if not client_id or client_id.strip() == "":
        return {
            "statusCode": 400,
            "body": {"error": "client_id is a required field"}
        }
    if not is_client_id_valid(client_id):
        return {
            "statusCode": 400,
            "body": {"error": "client_id must be alpha-numeric"}
        }
    # if user passed in a non-integer minimum_alive_secs, this line will error out
    minimum_alive_secs=config.DEFAULT_TOKEN_MIN_ALIVE_SECS if event.get('minimum_alive_secs') is None \
        else int(event.get('minimum_alive_secs'))
    # client_id must be alphanumeric
    if not is_minimum_alive_secs_valid(minimum_alive_secs):
        return {
            "statusCode": 422,
            "body":{"error": f"minimum_alive_secs if provided, must be numeric "
                                         f"and smaller or equal than {config.MAX_REQUESTED_ALIVE_SECS} secs"}
        }

    # Reconfigure the logger with the new log level
    logger = initialize_logger(log_level, client_id=client_id)
    # if the token expected to be expired shorter than the expiration time, then
    # get a new token, save new token to dynamoDB with new TTL
    # minimum_alive_secs:int|None = int(json.loads(event['body'])['minimum_alive_secs'])
    logger.debug(f"Context: {context}")
    logger.info(f'client_id: {client_id}  minimum_alive_secs: {minimum_alive_secs}')

    token_json = None
    # Retrieve token structure from DynamoDB using client_id
    try:
        # When a request comes in, check dynamoDB first, if not found then get new token
        token_structure_str:str = get_token_by_client_id(client_id)
        if token_structure_str is not None:
            token_json = json.loads(token_structure_str)
        if token_structure_str is not None and satisfy_minimum_alive_secs(int(token_json.get('expires_at')), minimum_alive_secs):
            logger.debug(f"Found token from cache which satisfied minimum alive secs: {minimum_alive_secs}")
            return token_json
        else:
            # retrieve new token , save to dynamoDB and return new token
            token_json = get_new_token(client_id) # this function will retrieve new token and save it to cache
            return token_json

    except Exception as e:
        logger.error(f"Error processing client_token: {str(e)}")
        raise e
