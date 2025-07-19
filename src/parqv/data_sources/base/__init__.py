"""
Base classes and interfaces for data sources.
"""

from .handler import DataHandler
from .exceptions import (
    DataSourceError,
    DataHandlerError,
    FileValidationError,
    UnsupportedFormatError,
    DataReadError,
    SchemaError,
    MetadataError,
)

__all__ = [
    # Base handler interface
    "DataHandler",
    
    # Exception classes
    "DataSourceError",
    "DataHandlerError",
    "FileValidationError",
    "UnsupportedFormatError",
    "DataReadError",
    "SchemaError",
    "MetadataError",
] 