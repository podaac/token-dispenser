"""
This module contains the main lambda functionality. the def handler(event, context):
is the AWS lambda entry point
"""
import logging
import json
import re
import tempfile
import time
from tempfile import NamedTemporaryFile
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from token_dispenser.aws.s3 import download_s3_file
from token_dispenser.aws.secret_manager import get_secret_value
from token_dispenser.launchpad_token import get_token
import token_dispenser.configuration as config
from token_dispenser.repository.token_repo import put_token, get_token_by_client_id
from token_dispenser.logging_config import initialize_logger, shared_logger
# pylint: disable=wrong-import-order


cached_cert_file: NamedTemporaryFile = None
# pylint: disable=R1732
temp_dir = tempfile.TemporaryDirectory()
# Set the logging level dynamically
log_level = getattr(logging, config.LOG_LEVEL)


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
    """
    Build a cached certificate file from private key and certificate.
    :param private_key:
    :param certificate:
    :return: NamedTemporaryFile containing the certificate and private key.
    """
    logger = shared_logger()
    # pylint: disable=global-statement
    global cached_cert_file
    try:
        logger.debug("entered build_cached_cert_file")
        # Serialize private key and certificate into PEM format
        private_key_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption()
        ).decode("utf-8")

        certificate_pem = certificate.public_bytes(Encoding.PEM).decode("utf-8")
        # Combine private key and certificate into a single file for mutual TLS authentication
        # The single file is managed by tempfile.NamedTemporaryFile where the library creates an
        # arbitrary file nd be responsible to remove the file while exiting the python virtual
        # machine even if exception happened
        if cached_cert_file is None:
            # NamedTemporaryFile default: delete=True. deletion after python exits
            # pylint: disable=R1732
            cached_cert_file = NamedTemporaryFile()
            cached_cert_file.write(private_key_pem.encode('utf-8'))
            cached_cert_file.write(certificate_pem.encode('utf-8'))
            cached_cert_file.flush()
            logger.info('cached certificate pem and private combination created.')
        else:
            logger.info('cached certificate pem and private combination already exists.')
            cached_cert_file.seek(0)  # reset file pointer
        return cached_cert_file
    except Exception as ex:
        logger.error(f"build_cached_cert_file error occurred: {str(ex)}")
        raise ex


def get_new_token(client_id: str):
    """
    obtain a new token based on client_id and write the newly obtained token into DynamoDB
    This function try to cache the cert file (a combination of private key and cert str).
    If the cached cert file exists,
    use the cached cert to get token.  Otherwise, go through pkc12 download, decode, build
    cert file and get token

    :param client_id: a required field which is used as key to cache the token in dynamoDB.
    :return: a json object containing the token data.
    """
    # pylint: disable=global-statement
    global cached_cert_file
    logger = shared_logger()
    token_json = None
    try:
        if cached_cert_file is not None:
            logger.debug(f"found cached cert file {cached_cert_file.name}")
            token_json = get_token(url=config.LAUNCHPAD_GETTOKEN_URL,
                                   cert_file=cached_cert_file.name)
        else:
            logger.debug("cached cert file not found")
            p12_file = download_s3_file(bucket_name=config.LAUNCHPAD_PFX_FILE_S3_BUCKET,
                                        key=config.LAUNCHPAD_PFX_FILE_S3_KEY,
                                        local_storage_dir=temp_dir.name)
            logger.info(f"p12 file downloaded from s3 successfully to: {p12_file}")
            password = get_secret_value(config.LAUNCHPAD_PFX_PASSWORD_SECRET_ARN)
            private_key, cert, _ = decode_pkcs12(p12_file, password)
            cached_cert_file = build_cached_cert_file(private_key, cert)
            # Create launchpad token
            token_json = get_token(url=config.LAUNCHPAD_GETTOKEN_URL,
                                   cert_file=cached_cert_file.name)
        put_token(client_id, json.dumps(token_json), int(token_json['expires_at']))
        return token_json
    except Exception as ex:
        logger.exception("Failed on get_new_token process")
        raise ex


def satisfy_minimum_alive_secs(expires_at: int, minimum_alive_secs: int) -> bool:
    """
    check if user input minimum_alive_secs expires
    :param expires_at:  the expires_at in seconds from token
    :param minimum_alive_secs:
    :return: True/False
    """
    # if the minimum_alive_sec is not provided by requester or value less than 0
    # it means the request does not care so we will assume whatever cached is ok
    if minimum_alive_secs is None or minimum_alive_secs <= 0:
        return True

    return expires_at - time.time() > minimum_alive_secs


def is_client_id_valid(client_id: str) -> bool:
    """
    check client_id is valid
    :param client_id: string to identify caller id
    :return: True/False
    """
    pattern = re.compile(r'^[a-zA-Z0-9]{3,32}$')
    return bool(pattern.match(client_id))


def is_minimum_alive_secs_valid(minimum_alive_secs: int) -> bool:
    """
    verify if user input minimum_alive_secs is valid
    :param minimum_alive_secs:
    :return: True/False
    """
    # If reached this point, minimum_alive_secs can not be NONE
    if not isinstance(minimum_alive_secs, int):
        return False

    return not ((isinstance(minimum_alive_secs, int) and
                (minimum_alive_secs > config.MAX_REQUESTED_ALIVE_SECS or minimum_alive_secs < 0)))


def handler(event, context):
    """
    Entry point of lambda function
    :param event:
    :param context:
    :return: Exception or json which represents a token structure
    """
    client_id = event.get('client_id')
    if not client_id or client_id.strip() == "":
        raise RuntimeError('client_id is a required field')

    if not is_client_id_valid(client_id):
        raise RuntimeError(
            'Invalid client_id. Client IDs must be alphanumeric and between 3 '
            'and 32 characters in length.'
        )

    # if user passed in a non-integer minimum_alive_secs, this line will error out
    minimum_alive_secs = config.MINIMUM_ALIVE_SECS if event.get('minimum_alive_secs') is None \
        else int(event.get('minimum_alive_secs'))
    # client_id must be alphanumeric
    if not is_minimum_alive_secs_valid(minimum_alive_secs):
        raise RuntimeError(
            f'minimum_alive_secs, if provided, must be numeric and smaller than '
            f'or equal to {config.MAX_REQUESTED_ALIVE_SECS} secs'
        )

    # Reconfigure the logger with the new log level
    logger = initialize_logger(log_level, client_id=client_id)
    logger.debug(f"Context: {context}")
    logger.info(f'client_id: {client_id}  minimum_alive_secs: {minimum_alive_secs}')

    token_json = None
    # Retrieve token structure from DynamoDB using client_id
    try:
        # When a request comes in, check dynamoDB first, if not found then get new token
        token_structure_str: str = get_token_by_client_id(client_id)
        if token_structure_str is not None:
            token_json = json.loads(token_structure_str)
            if (satisfy_minimum_alive_secs(int(token_json.get('expires_at')),
                                           minimum_alive_secs)):
                logger.debug(f"Found token from cache which satisfied minimum alive secs:"
                             f" {minimum_alive_secs}")
                return token_json
        # Not finding token from dynamoDB, hence retrieve new token,
        # save to dynamoDB and return new token
        token_json = get_new_token(client_id)
        return token_json

    except Exception as ex:
        logger.error(f"Error processing client_token: {str(ex)}")
        raise ex
