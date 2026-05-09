# This is a replacement for the LOGGING section in settings.py
# Add this to your settings.py

import os
from .logging_config import setup_logging, get_logger

# Configure structured logging
LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'text' or 'json'
LOG_LEVEL = os.getenv('LOG_LEVEL', None)

# Setup logging
setup_logging(
    debug=DEBUG,
    log_level=LOG_LEVEL,
    log_format=LOG_FORMAT
)

# Logger for this module
logger = get_logger(__name__)

# Example of using the logger:
# logger.info("Application started", extra={'component': 'settings'})
