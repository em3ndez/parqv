"""
Core modules for parqv application.

This package contains fundamental configuration, utilities, and factory classes.
"""

from .config import SUPPORTED_EXTENSIONS, DEFAULT_PREVIEW_ROWS, CSS_PATH
from .logging import setup_logging, get_logger
from .file_utils import FileValidationError, validate_and_detect_file, validate_file_path, detect_file_type
from .handler_factory import HandlerFactory, HandlerCreationError

__all__ = [
    # Configuration
    "SUPPORTED_EXTENSIONS",
    "DEFAULT_PREVIEW_ROWS", 
    "CSS_PATH",
    
    # Logging
    "setup_logging",
    "get_logger",
    
    # File utilities
    "FileValidationError",
    "validate_and_detect_file",
    "validate_file_path",
    "detect_file_type",
    
    # Factory
    "HandlerFactory",
    "HandlerCreationError",
] 