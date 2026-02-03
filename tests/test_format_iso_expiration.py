"""Unit tests for format_iso_expiration_date function."""

# pylint: disable=import-error

import os
import unittest
from datetime import datetime
from unittest.mock import patch
from dateutil import parser  # type: ignore

from token_dispenser.token_dispenser_lambda import format_iso_expiration_date


@patch.dict(
    os.environ,
    {
        "LAUNCHPAD_PFX_PASSWORD_SECRET_ARN": "",
        "LAUNCHPAD_PFX_FILE_S3_BUCKET": "",
        "LAUNCHPAD_PFX_FILE_S3_KEY": "",
        "DYNAMO_DB_CACHE_TABLE_NAME": "",
    },
)
class TestFormatIsoExpirationDate(unittest.TestCase):
    """
    Test class for TestFormatIsoExpirationDate
    """

    # ------------------------------------------------------------------
    # Happy-path tests
    # ------------------------------------------------------------------
    def test_valid_inputs(self):
        """Test valid inputs."""
        test_cases = [
            ("2025-12-31T23:59:59Z", "12/31/2025"),
            ("2025-12-31T23:59:59.123Z", "12/31/2025"),
            ("12/31/2025", "12/31/2025"),
            ("2025-12-31", "12/31/2025"),
            ("March 1, 2025", "03/01/2025"),
            (datetime(2025, 12, 31), "12/31/2025"),
        ]

        for input_value, expected in test_cases:
            with self.subTest(input_value=input_value):
                self.assertEqual(format_iso_expiration_date(input_value), expected)

    # ------------------------------------------------------------------
    # Invalid string input
    # ------------------------------------------------------------------
    def test_invalid_strings(self):
        """Docstring for test_invalid_strings"""
        invalid_strings = [
            "not-a-date",
            "2025-13-01T00:00:00Z",
            "2025-02-30",
            "",
        ]

        for input_value in invalid_strings:
            with self.subTest(input_value=input_value):
                with self.assertRaisesRegex(ValueError, "Cannot parse date/time"):
                    format_iso_expiration_date(input_value)

    # ------------------------------------------------------------------
    # Non-string, non-datetime inputs
    # ------------------------------------------------------------------
    def test_invalid_types(self):
        """Docstring for test_invalid_types"""
        invalid_types = [
            123,
            45.6,
            None,
            ["2025-12-31"],
            {"date": "2025-12-31"},
        ]

        for input_value in invalid_types:
            with self.subTest(input_value=input_value):
                with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
                    format_iso_expiration_date(input_value)

    # ------------------------------------------------------------------
    # ISO parsing parity
    # ------------------------------------------------------------------
    def test_matches_dateutil_parser(self):
        """Docstring for test_matches_dateutil_parser"""
        iso_string = "2025-10-25T00:00:00Z"
        expected = parser.isoparse(iso_string).strftime("%m/%d/%Y")

        self.assertEqual(format_iso_expiration_date(iso_string), expected)

    def test_timezone_aware_iso_string(self):
        """Docstring for test_timezone_aware_iso_string"""
        iso_string = "2025-10-25T12:00:00+05:00"
        expected = "10/25/2025"

        self.assertEqual(format_iso_expiration_date(iso_string), expected)

    def test_leap_year_date(self):
        """Docstring for test_leap_year_date"""
        iso_string = "2024-02-29T00:00:00Z"
        expected = "02/29/2024"

        self.assertEqual(format_iso_expiration_date(iso_string), expected)

    def test_end_of_month_date(self):
        """Docstring for test_end_of_month_date"""
        iso_string = "2025-04-30T23:59:59Z"
        expected = "04/30/2025"

        self.assertEqual(format_iso_expiration_date(iso_string), expected)

    # ------------------------------------------------------------------
    # Invalid datetime-like objects
    # ------------------------------------------------------------------
    def test_invalid_datetime_object(self):
        """Docstring for test_invalid_datetime_object"""

        class InvalidDateTime:
            """Docstring for InvalidDateTime"""

        with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
            format_iso_expiration_date(InvalidDateTime())

    def test_empty_string(self):
        """Docstring for test_empty_string"""
        with self.assertRaisesRegex(ValueError, "Cannot parse date/time"):
            format_iso_expiration_date("")

    def test_none_input(self):
        """Docstring for test_none_input"""
        with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
            format_iso_expiration_date(None)

    def test_numeric_input(self):
        """Docstring for test_numeric_input"""
        with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
            format_iso_expiration_date(12345)

    def test_incorrect_format_string(self):
        """Docstring for test_incorrect_format_string"""
        self.assertEqual(format_iso_expiration_date("31-12-2025"), "12/31/2025")

    def test_non_date_string(self):
        """Docstring for test_non_date_string"""
        with self.assertRaisesRegex(ValueError, "Cannot parse date/time"):
            format_iso_expiration_date("Hello, World!")

    def test_list_input(self):
        """Docstring for test_list_input"""
        with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
            format_iso_expiration_date(["2025-12-31"])

    def test_dict_input(self):
        """Docstring for test_dict_input"""
        with self.assertRaisesRegex(TypeError, "Input must be a string or datetime"):
            format_iso_expiration_date({"date": "2025-12-31"})


if __name__ == "__main__":
    unittest.main()
