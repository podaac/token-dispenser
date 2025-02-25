import logging
from logging import Formatter, LogRecord, LoggerAdapter
from typing import Optional
import threading

# Global variables to hold logger instance and lock for thread-safety
_logger_instance: Optional[LoggerAdapter] = None
_lock = threading.Lock()
_global_client_id:str=''

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
    global _global_client_id
    print('Initializing logger_config')
    with _lock:
        if _logger_instance is None:
            print('Entering logger while it is NONE')
            _global_client_id = client_id
            # Create the logger only if it hasn't been created yet
            logger = logging.getLogger("TDS_Logger")
            if not logger.hasHandlers():
                print('logger does not have handlers, initializing handler')
                logger.setLevel(log_level)
                print('1')
                console_handler = logging.StreamHandler()
                print('1.1')
                console_handler.setLevel(log_level)
                print('1.2')
                formatter = CustomFormatter('%(levelname)s - client_id: %(client_id)s - %(message)s')
                print('1.3')
                console_handler.setFormatter(formatter)
                print('1.4')
                logger.addHandler(console_handler)
                print('1.5')
            else:
                print('2')
                return CustomLoggerAdapter(logger, {"client_id": client_id})
            print('3')
            _logger_instance = CustomLoggerAdapter(logger, {"client_id": client_id})
        else:
            print('4')
            _global_client_id = client_id
            # If logger already exists, update the client_id and log level dynamically
            _logger_instance.logger.setLevel(log_level)
            for handler in _logger_instance.logger.handlers:
                handler.setLevel(log_level)
            _logger_instance.extra['client_id'] = client_id
            print(f"Updated logger: client_id={client_id}, log_level={logging.getLevelName(log_level)}")
    print('Returning logger_config')
    return _logger_instance


# Function to get the current logger instance
def shared_logger() -> LoggerAdapter:
    global _logger_instance
    if _logger_instance is None:
        # Initialize with default settings if not initialized yet
        return initialize_logger()
    return _logger_instance