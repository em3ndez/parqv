"""
parqv - A Textual application for visualizing Parquet and JSON files.
"""

from .app import ParqV
from .cli import run_app
from .core import (
    SUPPORTED_EXTENSIONS, 
    DEFAULT_PREVIEW_ROWS,
    FileValidationError, 
    validate_and_detect_file,
    HandlerFactory, 
    HandlerCreationError,
    setup_logging, 
    get_logger
)

__version__ = "1.0.0"

__all__ = [
    "ParqV",
    "run_app", 
    "SUPPORTED_EXTENSIONS",
    "DEFAULT_PREVIEW_ROWS",
    "FileValidationError",
    "validate_and_detect_file",
    "HandlerFactory",
    "HandlerCreationError",
    "setup_logging",
    "get_logger",
]
