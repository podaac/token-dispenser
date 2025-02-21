
import json
from tempfile import NamedTemporaryFile
import time
import requests
import logging
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

def get_token(url:str, private_key, certificate):
    """
    Access the /gettoken endpoint using the provided private key and certificate to obtain a token.

    :param url: The URL of the /gettoken endpoint.
    :param private_key: The private key object (from cryptography.hazmat.primitives.asymmetric).
    :param certificate: The certificate object (from cryptography.x509).

    :return: The token response as a string.
    """
    try:
        logging.debug(f"entered get_token")
        # Serialize private key and certificate into PEM format
        private_key_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption()
        ).decode("utf-8")

        certificate_pem = certificate.public_bytes(Encoding.PEM).decode("utf-8")
        # Combine private key and certificate into a single file for mutual TLS authentication
        # The single file is managed by tempfile.NamedTemporaryFile where the library creates an arbitrary file
        # and be responsible to remove the file while leaving the code block even if exception happened
        # pem_file_path = '/tmp/temp_cert.pem'
        with NamedTemporaryFile(delete=True) as pem_file:
            pem_file.write(private_key_pem.encode('utf-8'))
            pem_file.write(certificate_pem.encode('utf-8'))
            pem_file.flush()
            logging.info("certificate pem and private combination created. Preparing for /gettoken call")
            response = requests.get(
                url,
                cert=pem_file.name,
                verify=True
            )
            # Check if the request was successful
            if response.status_code == 200:
                logging.info("Successfully obtained token.")
                content_str: str = response.content.decode('utf-8')
                # Parse the string into a JSON object
                json_data = json.loads(content_str)
                current_time: int = int(time.time())
                json_data['expires_at'] = current_time + int(json_data['session_maxtimeout'])
                json_data['created_at'] = current_time
                return json_data
            else:
                logging.info("launchpad /gettoken call failed")
                return f"Failed to obtain token. HTTP Status: {response.status_code}, Response: {response.text}"
    except Exception as e:
        logging.info(f"get_token error occurred: {str(e)}")
        raise e