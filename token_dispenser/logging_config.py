"""
This module provides application level logging abilities with
input client_id always within each log output statement
"""
import logging
from logging import Formatter, LogRecord, LoggerAdapter
from typing import Optional

# Global variables to hold logger instance and lock for thread-safety
_logger_instance: Optional[LoggerAdapter] = None


class CustomFormatter(Formatter):
    def format(self, record: LogRecord) -> str:
        record.client_id = getattr(record, 'client_id', 'N/A')
        return super().format(record)


class CustomLoggerAdapter(LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs['extra'] = kwargs.get('extra', {})
        kwargs['extra']['client_id'] = self.extra['client_id']
        return msg, kwargs


def initialize_logger(log_level=logging.INFO, client_id='N/A') -> LoggerAdapter:
    global _logger_instance
    if _logger_instance is None:
        # Create the logger only if it hasn't been created yet
        logger = logging.getLogger("TDS_Logger")
        logger.propagate = False
        if not logger.hasHandlers():
            logger.setLevel(log_level)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            formatter = CustomFormatter('%(levelname)s - client_id: %(client_id)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            return CustomLoggerAdapter(logger, {"client_id": client_id})
        _logger_instance = CustomLoggerAdapter(logger, {"client_id": client_id})
    else:
        # If logger already exists, update the client_id and log level dynamically
        _logger_instance.logger.setLevel(log_level)
        for handler in _logger_instance.logger.handlers:
            handler.setLevel(log_level)
        _logger_instance.extra['client_id'] = client_id
    return _logger_instance


# Function to get the current logger instance
def shared_logger() -> LoggerAdapter:
    global _logger_instance
    if _logger_instance is None:
        # Initialize with default settings if not initialized yet
        return initialize_logger()
    return _logger_instance
