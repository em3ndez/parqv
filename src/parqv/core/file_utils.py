"""
File utilities for parqv application.
"""

from pathlib import Path
from typing import Optional, Tuple

from .config import SUPPORTED_EXTENSIONS
from .logging import get_logger

log = get_logger(__name__)


class FileValidationError(Exception):
    """Exception raised when file validation fails."""
    pass


def validate_file_path(file_path_str: Optional[str]) -> Path:
    """
    Validates and resolves the file path.
    
    Args:
        file_path_str: String representation of the file path
        
    Returns:
        Resolved Path object
        
    Raises:
        FileValidationError: If file path is invalid or file doesn't exist
    """
    if not file_path_str:
        raise FileValidationError("No file path provided.")
    
    file_path = Path(file_path_str)
    log.debug(f"Validating file path: {file_path}")
    
    if not file_path.is_file():
        raise FileValidationError(f"File not found or is not a regular file: {file_path}")
    
    return file_path


def detect_file_type(file_path: Path) -> str:
    """
    Detects the file type based on its extension.
    
    Args:
        file_path: Path object representing the file
        
    Returns:
        String representing the detected file type ('parquet' or 'json')
        
    Raises:
        FileValidationError: If file extension is not supported
    """
    file_suffix = file_path.suffix.lower()
    
    if file_suffix not in SUPPORTED_EXTENSIONS:
        supported_exts = ", ".join(SUPPORTED_EXTENSIONS.keys())
        raise FileValidationError(
            f"Unsupported file extension: '{file_suffix}'. "
            f"Only {supported_exts} are supported."
        )
    
    detected_type = SUPPORTED_EXTENSIONS[file_suffix]
    log.info(f"Detected '{file_suffix}' extension, type: {detected_type}")
    
    return detected_type


def validate_and_detect_file(file_path_str: Optional[str]) -> Tuple[Path, str]:
    """
    Convenience function that validates file path and detects file type.
    
    Args:
        file_path_str: String representation of the file path
        
    Returns:
        Tuple of (validated_path, detected_type)
        
    Raises:
        FileValidationError: If validation or type detection fails
    """
    file_path = validate_file_path(file_path_str)
    file_type = detect_file_type(file_path)
    
    return file_path, file_type 