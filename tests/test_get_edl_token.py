"""
Docstring for tests.test_get_edl_token
"""

# pylint: disable=line-too-long

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import set_env
from token_dispenser.token_dispenser_lambda import get_edl_token
import token_dispenser.token_dispenser_lambda


class TestGetEdlToken(unittest.TestCase):
    """Unit tests for get_edl_token function."""

    def setUp(self):
        token_dispenser.token_dispenser_lambda.EDL_USER_TOKEN = None

    @patch("token_dispenser.token_dispenser_lambda.put_token", new_callable=MagicMock)
    @patch("token_dispenser.token_dispenser_lambda.shared_logger")
    @patch("token_dispenser.token_dispenser_lambda.requests.Session")
    def test_create_new_token(
        self,
        mock_session_class,
        mock_logger,
        mock_put_token,
    ):
        """Test creating a new token when none exists."""

        fake_now = datetime(2025, 1, 1)

        # Patch datetime inside the test
        with patch("token_dispenser.token_dispenser_lambda.datetime") as mock_datetime:
            mock_datetime.now.return_value = fake_now
            mock_datetime.strptime = datetime.strptime

            # Mock session
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session

            # POST create token returns a new token
            new_token_data = {
                "access_token": "new_access_token",
                "expiration_date": (fake_now + timedelta(days=1)).strftime(
                    "%m/%d/%Y"
                ),
            }
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = new_token_data
            mock_post_response.raise_for_status.return_value = None
            mock_session.post.return_value = mock_post_response
            mock_session.request.return_value = mock_post_response

            token = get_edl_token("client_id", "user", "pass", "UAT")

            # Assertions: function returns access_token string
            self.assertEqual(token, "new_access_token")
            mock_put_token.assert_called_once()  # ensure token was stored


if __name__ == "__main__":
    unittest.main()
