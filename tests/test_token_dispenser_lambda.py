"""
Test class for token_dispenser_lambda
"""
import sys
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import time
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# Import the environment variables setup file
import set_env  # noqa: F401, E402

import token_dispenser.configuration as config  # noqa: E402
from token_dispenser.token_dispenser_lambda import (  # noqa: E402
    decode_pkcs12,
    build_cached_cert_file,
    get_new_token,
    satisfy_minimum_alive_secs,
    is_client_id_valid,
    is_minimum_alive_secs_valid,
    handler
)


class TestTokenDispenserLambda(unittest.TestCase):
    """
    Test class for token_dispenser_lambda
    """

    @patch("token_dispenser.token_dispenser_lambda.load_key_and_certificates")
    @patch("builtins.open", new_callable=mock_open, read_data=b"pkcs12_data")
    def test_decode_pkcs12(self, mock_file, mock_load):
        """test the function which decodes pkcs12 file"""
        mock_private_key = MagicMock()
        mock_certificate = MagicMock()
        mock_additional_certs = MagicMock()
        mock_load.return_value = (mock_private_key, mock_certificate, mock_additional_certs)
        private_key, certificate, additional_certs = decode_pkcs12("test.p12", "password")
        self.assertEqual(private_key, mock_private_key, "The private_key does not match the expected mock object.")
        self.assertEqual(certificate, mock_certificate, "The certificate does not match the expected mock object.")
        self.assertEqual(additional_certs, mock_additional_certs, "The additional_certs do not match the expected mock object.")
        

    @patch("token_dispenser.token_dispenser_lambda.shared_logger")
    def test_build_cached_cert_file_new(self, mock_logger):
        """test the function which builds cached cert file"""
        mock_private_key = MagicMock()
        mock_certificate = MagicMock()
        mock_private_key.private_bytes.return_value = b"private_key_pem"
        mock_certificate.public_bytes.return_value = b"certificate_pem"

        result = build_cached_cert_file(mock_private_key, mock_certificate)
        result.seek(0)
        content = result.read()
        self.assertTrue(content == b"private_key_pemcertificate_pem")
        self.assertTrue(os.path.exists(result.name))
        self.assertTrue(os.path.getsize(result.name) > 0)

    @patch("token_dispenser.token_dispenser_lambda.get_token")
    @patch("token_dispenser.token_dispenser_lambda.build_cached_cert_file")
    @patch("token_dispenser.token_dispenser_lambda.decode_pkcs12")
    @patch("token_dispenser.token_dispenser_lambda.download_s3_file")
    @patch("token_dispenser.token_dispenser_lambda.get_secret_value")
    @patch("token_dispenser.token_dispenser_lambda.put_token")
    @patch("token_dispenser.token_dispenser_lambda.get_token_by_client_id")
    # pylint: disable=too-many-arguments
    def test_get_new_token_new(self, mock_get_db_token, mock_put_db_token, mock_get_secret,
                               mock_download_s3,
                               mock_decode_p12, mock_build_cache, mock_get_token):
        """test get new token function"""
        mock_get_db_token.return_value = None
        mock_download_s3.return_value = "/tmp/test.p12"
        mock_get_secret.return_value = "password"
        mock_private_key = MagicMock()
        mock_certificate = MagicMock()
        mock_decode_p12.return_value = (mock_private_key, mock_certificate, MagicMock())
        mock_cache_file = MagicMock()
        mock_cache_file.name = "cache.pem"
        mock_build_cache.return_value = mock_cache_file
        mock_get_token.return_value = {"token": "test_token", "expires_at": int(time.time() + 3600)}

        result = get_new_token("test_client")

        self.assertEqual(result, {"token": "test_token", "expires_at": int(time.time() + 3600)})
        mock_put_db_token.assert_called_once()

    def test_satisfy_minimum_alive_secs(self):
        """test minimum_alive_secs is satisfied or not"""
        self.assertTrue(satisfy_minimum_alive_secs(int(time.time() + 1000), 100))
        self.assertFalse(satisfy_minimum_alive_secs(int(time.time() + 50), 100))
        self.assertTrue(satisfy_minimum_alive_secs(int(time.time() + 50), -1))

    def test_is_client_id_valid(self):
        """test client_id validation"""
        self.assertTrue(is_client_id_valid("validid"))
        self.assertTrue(is_client_id_valid("validid00"))
        self.assertTrue(is_client_id_valid("123validid"))
        self.assertFalse(is_client_id_valid("invalid-id!"))

    def test_is_minimum_alive_secs_valid(self):
        """test minimum_alive_secs validation"""
        config.MAX_REQUESTED_ALIVE_SECS = 3600
        self.assertTrue(is_minimum_alive_secs_valid(100))
        self.assertFalse(is_minimum_alive_secs_valid(4000))
        self.assertFalse(is_minimum_alive_secs_valid(-10))
        self.assertFalse(is_minimum_alive_secs_valid(10.5))

    @patch("token_dispenser.token_dispenser_lambda.get_new_token")
    @patch("token_dispenser.token_dispenser_lambda.get_token_by_client_id")
    @patch("token_dispenser.token_dispenser_lambda.initialize_logger")
    def test_handler(self, mock_logger, mock_get_db_token, mock_get_new_token):
        """ test lambda handler"""
        current_time_plus_one_hour:int  = int(time.time()) + 3600
        mock_get_db_token.return_value = json.dumps({"expires_at": current_time_plus_one_hour})
        event = {"client_id": "testclient", "minimum_alive_secs": 100}
        result = handler(event, MagicMock())
        self.assertEqual(type(result), dict)
        self.assertTrue(result['expires_at'], current_time_plus_one_hour)
