import logging
from logging import Formatter, LogRecord, LoggerAdapter

from typing import Optional
GLOBAL_CLIENT_ID = 'N/A'
GLOBAL_ADAPTER: Optional['CustomLoggerAdapter'] = None


class CustomFormatter(Formatter):
    def format(self, record: LogRecord) -> str:
        # Add custom attributes to the log record
        record.client_id = getattr(record, 'client_id', 'N/A')
        return super().format(record)


class CustomLoggerAdapter(LoggerAdapter):
    def process(self, msg, kwargs):
        # Add custom attributes to the logging message
        kwargs['extra'] = kwargs.get('extra', {})
        kwargs['extra']['client_id'] = self.extra['client_id']
        return msg, kwargs


def configure_logger(log_level=logging.INFO, client_id='N/A'):
    global GLOBAL_CLIENT_ID
    global GLOBAL_ADAPTER
    GLOBAL_CLIENT_ID = client_id
    # Create a logger
    logger = logging.getLogger('TDS_Logger')

    # Set the logging level
    logger.setLevel(log_level)
    # Check if the logger already has handlers
    if not logger.hasHandlers():
        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Create and set a custom formatter
        formatter = CustomFormatter('%(levelname)s - client_id: %(client_id)s - %(message)s')
        console_handler.setFormatter(formatter)

        # Add the console handler to the logger
        logger.addHandler(console_handler)

    # Create a logger adapter with additional context
    GLOBAL_ADAPTER = CustomLoggerAdapter(logger, {'client_id': GLOBAL_CLIENT_ID})
    return GLOBAL_ADAPTER

def get_logger_adapter() -> CustomLoggerAdapter:
    global GLOBAL_CLIENT_ID
    return configure_logger(logging.DEBUG, GLOBAL_CLIENT_ID)

# Singleton instance of the logger adapter
logger_adapter = configure_logger()