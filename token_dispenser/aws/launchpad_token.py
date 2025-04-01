"""
This module accesses the /gettoken endpoint from launchpad application to obtain
Launchpad Token
"""
import json
import time
import requests
from token_dispenser.logging_config import shared_logger


def get_token(url: str, cert_file: str):
    """
    Access the /gettoken endpoint using the provided private key and certificate to obtain a token.

    :param url: The URL of the /gettoken endpoint.
    :param cert_file: the full path to a certificate file containing both cert string and
    private key.

    :return: The token response as a dict.
    """
    logger = shared_logger()
    logger.debug(f"Trying to obtain a token from {url}")
    # Serialize private key and certificate into PEM format

    response = requests.get(
        url,
        cert=cert_file,
        timeout=10  # timeout of 10 seconds
    )
    # Check if the request was successful
    if response.status_code == 200:
        logger.info("Successfully obtained token.")
        content_str: str = response.content.decode('utf-8')
        # Parse the string into a JSON object
        json_data = json.loads(content_str)
        current_time: int = int(time.time())
        json_data['expires_at'] = current_time + int(json_data['session_maxtimeout'])
        json_data['created_at'] = current_time
        return json_data

    logger.error("launchpad /gettoken call failed with code {response.status_code}")
    response.raise_for_status()

