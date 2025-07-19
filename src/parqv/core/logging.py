"""
Logging configuration for parqv application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import LOG_FILENAME, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_ENCODING


def setup_logging() -> logging.Logger:
    """
    Sets up logging configuration for the parqv application.
    
    Returns:
        The root logger instance configured for parqv.
    """
    file_handler = RotatingFileHandler(
        LOG_FILENAME, 
        maxBytes=LOG_MAX_BYTES, 
        backupCount=LOG_BACKUP_COUNT, 
        encoding=LOG_ENCODING
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-5.5s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
        handlers=[file_handler, logging.StreamHandler(sys.stdout)],
        force=True  # Override any existing configuration
    )
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """
    Gets a logger instance for the given name.
    
    Args:
        name: The name for the logger (typically __name__)
        
    Returns:
        A logger instance.
    """
    return logging.getLogger(name) 