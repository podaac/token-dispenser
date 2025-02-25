"""Unit tests for the token_dispenser_lambda.py module"""

# Set environment variables
import os
os.environ['AWS_REGION'] = 'us-west-2'
os.environ['DYNAMO_DB_CACHE_TABLE_NAME'] = 'sndbx-LaunchpadTokenDispenserCacheTable'
os.environ['LOG_LEVEL'] = 'INFO'
import pytest
from token_dispenser.token_dispenser_lambda import (decode_pkcs12, get_new_token, satisfy_minimum_alive_secs,
    is_client_id_valid, is_minimum_alive_secs_valid, handler)
import token_dispenser.configuration as configuration
import json
from unittest.mock import patch, MagicMock
import time
import unittest


@pytest.fixture(scope="session")
def data_dir():
    """Test data directory."""
    test_dir = os.path.dirname(os.path.realpath(__file__))
    yield os.path.join(test_dir, 'data')


def test_satisfy_minimum_alive_secs(data_dir):
    """Assert the correct satisfy_minimum_alive_secs function is called"""
    full_path = os.path.join(data_dir, 'sample_token.json')
    with open(full_path, 'r') as file:
        data = file.read().replace('\n', '')

    token_json = json.loads(data)
    is_satisfy_minimum_alive_secs = satisfy_minimum_alive_secs(token_json,None)
    assert is_satisfy_minimum_alive_secs == True
    is_satisfy_minimum_alive_secs = satisfy_minimum_alive_secs(token_json, -1)
    assert is_satisfy_minimum_alive_secs == True
    is_satisfy_minimum_alive_secs = satisfy_minimum_alive_secs(token_json, 100)
    assert is_satisfy_minimum_alive_secs == False

def test_is_client_id_valid():
    assert is_client_id_valid('abc') == True
    assert is_client_id_valid('1234567890') == True
    assert is_client_id_valid('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa') == False
    assert is_client_id_valid('ab') == False
    assert is_client_id_valid('a_b') == False
    assert is_client_id_valid('aBcDeFgHiJkLmNoPqRsTuVwXy') == True


def test_is_minimum_alive_secs_valid():
    """Assert the correct is_minimum_alive_secs_valid function is called"""
    # None is acceptable because minimum_alive_secs is not a required field
    is_valid:bool = is_minimum_alive_secs_valid(None)
    assert is_valid == True
    is_valid = is_minimum_alive_secs_valid(0)
    assert is_valid == True
    # Input negative minimum_alive_secs value is not allowed
    is_valid = is_minimum_alive_secs_valid(-2)
    assert is_valid == False
    # Number smaller than SESSION_MAXTIMEOUT is allowed
    is_valid = is_minimum_alive_secs_valid(configuration.SESSION_MAXTIMEOUT -2)
    assert is_valid == True
    # Number greater than SESSION_MAXTIMEOUT is not allowed
    is_valid = is_minimum_alive_secs_valid(configuration.SESSION_MAXTIMEOUT +3)
    assert is_valid == False

@patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"mocked_p12_data")
@patch("token_dispenser.token_dispenser_lambda.load_key_and_certificates")
def test_decode_pkcs12(mock_load_key_and_certificates, mock_open):
    mock_load_key_and_certificates.return_value = ("private_key", "certificate", "additional_certs")
    private_key, certificate, additional_certs = decode_pkcs12("mocked_path.p12", "password")
    assert private_key == "private_key"
    assert certificate == "certificate"
    assert additional_certs == "additional_certs"

@patch("token_dispenser.token_dispenser_lambda.download_s3_file")
@patch("token_dispenser.token_dispenser_lambda.get_secret_value")
@patch("token_dispenser.token_dispenser_lambda.decode_pkcs12")
@patch("token_dispenser.token_dispenser_lambda.get_token")
@patch("token_dispenser.token_dispenser_lambda.put_token")
@patch("token_dispenser.token_dispenser_lambda.shared_logger")
def test_get_new_token(mock_shared_logger, mock_put_token, mock_get_token,
                       mock_decode_pkcs12, mock_get_secret_value, mock_download_s3_file):
    mock_shared_logger.return_value = MagicMock()
    mock_download_s3_file.return_value = "mocked_p12_path"
    mock_get_secret_value.return_value = "mocked_password"
    mock_decode_pkcs12.return_value = ("private_key", "certificate", "additional_certs")
    mock_get_token.return_value = {"token": "mocked_token", "expires_at": time.time() + 3600}

    token_json = get_new_token("mocked_client_id")
    assert token_json["token"] == "mocked_token"


@patch("token_dispenser.token_dispenser_lambda.get_token_by_client_id")
@patch("token_dispenser.token_dispenser_lambda.satisfy_minimum_alive_secs")
@patch("token_dispenser.token_dispenser_lambda.get_new_token")
@patch("token_dispenser.token_dispenser_lambda.is_client_id_valid")
@patch("token_dispenser.token_dispenser_lambda.is_minimum_alive_secs_valid")
@patch("token_dispenser.token_dispenser_lambda.initialize_logger")
@patch("token_dispenser.token_dispenser_lambda.config")
def test_handler(mock_config, mock_initialize_logger, mock_is_minimum_alive_secs_valid,
                 mock_is_client_id_valid, mock_get_new_token, mock_satisfy_minimum_alive_secs,
                 mock_get_token_by_client_id):
    mock_config.DEFAULT_TOKEN_MIN_ALIVE_SECS = 300
    mock_config.MAX_REQUESTED_ALIVE_SECS = 3600
    mock_config.AWS_REGION = "us-west-2"
    mock_config.DYNAMO_DB_CACHE_TABLE_NAME = "mocked_table"
    mock_initialize_logger.return_value = MagicMock()
    mock_is_client_id_valid.return_value = True
    mock_is_minimum_alive_secs_valid.return_value = True
    mock_get_token_by_client_id.return_value = json.dumps({"token": "cached_token", "expires_at": time.time() + 3600})
    mock_satisfy_minimum_alive_secs.return_value = True

    event = {
        "client_id": "validClientID123",
        "minimum_alive_secs": 1800
    }
    context = {}

    response = handler(event, context)
    assert response == json.dumps({"token": "cached_token", "expires_at": time.time() + 3600})
