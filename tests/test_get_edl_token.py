"""
Docstring for tests.test_get_edl_token
"""

# pylint: disable=line-too-long

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from token_dispenser.token_dispenser_lambda import get_edl_token
import token_dispenser.token_dispenser_lambda


class TestGetEdlToken(unittest.TestCase):
    """Unit tests for get_edl_token function."""

    def setUp(self):
        token_dispenser.token_dispenser_lambda.EDL_USER_TOKEN = None

    @patch("token_dispenser.token_dispenser_lambda.json.dumps", return_value="{}")
    @patch("token_dispenser.token_dispenser_lambda.requests.Session")
    @patch(
        "token_dispenser.token_dispenser_lambda.format_iso_expiration_date",
        side_effect=lambda x: x,
    )
    @patch("token_dispenser.token_dispenser_lambda.shared_logger")
    @patch("token_dispenser.token_dispenser_lambda.put_token", new_callable=MagicMock)
    def test_create_new_token(
        self,
        mock_put_token,
        mock_logger,
        mock_format_date,
        mock_session_class,
        mock_json_dumps,
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

            # GET returns empty tokens list
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = []
            mock_get_response.raise_for_status.return_value = None
            mock_session.get.return_value = mock_get_response
            mock_session.request.return_value = mock_get_response

            # POST create token returns a new token
            new_token_data = {
                "access_token": "new_access_token",
                "expiration_date": (fake_now + timedelta(days=1)).strftime(
                    "%m/%d/%Y"
                ),  # string to avoid JSON error
            }
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = new_token_data
            mock_post_response.raise_for_status.return_value = None
            mock_session.post.return_value = mock_post_response
            mock_session.request.return_value = mock_post_response

            token = get_edl_token("user", "pass", "UAT")

            # Assertions
            self.assertEqual(token["access_token"], "new_access_token")
            self.assertEqual(
                token["expiration_date"].strftime("%m/%d/%Y"),
                (fake_now + timedelta(days=1)).strftime("%m/%d/%Y"),
            )
            mock_put_token.assert_called_once()  # ensure token was stored

    @patch("token_dispenser.token_dispenser_lambda.put_token", new_callable=MagicMock)
    @patch("token_dispenser.token_dispenser_lambda.shared_logger")
    @patch(
        "token_dispenser.token_dispenser_lambda.format_iso_expiration_date",
        side_effect=lambda x: x,
    )
    @patch("token_dispenser.token_dispenser_lambda.requests.Session")
    def test_return_cached_token(
        self, mock_session_class, mock_format_date, mock_logger, mock_put_token
    ):
        """Test returning a cached token if it is still valid."""
        fake_now = datetime(2025, 1, 1)

        # Update the global cached token
        token_dispenser.token_dispenser_lambda.EDL_USER_TOKEN = {
            "access_token": "cached_token",
            "expiration_date": fake_now + timedelta(days=1),
        }

        with patch("token_dispenser.token_dispenser_lambda.datetime") as mock_datetime:
            mock_datetime.now.return_value = fake_now
            mock_datetime.strptime = datetime.strptime

            token = get_edl_token("user", "pass", "UAT")

            # Print token for debugging
            print(f"token: {token}", flush=True)

            self.assertIsInstance(token, dict)
            self.assertIn(token["access_token"], ["cached_token", "new_access_token"])

            # No new token should have been created
            mock_put_token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
