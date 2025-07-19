"""
Data sources package for parqv application.

This package provides adapters for various data file formats,
offering a unified interface for data access.
"""

# Base classes and exceptions
from .base import (
    DataHandler,
    DataHandlerError,
    DataSourceError,
    FileValidationError,
    UnsupportedFormatError,
    DataReadError,
    SchemaError,
    MetadataError,
)

# Format-specific handlers
from .formats import (
    ParquetHandler,
    ParquetHandlerError,
    JsonHandler,
    JsonHandlerError,
    CsvHandler,
    CsvHandlerError,
)

__all__ = [
    # Base interface and exceptions
    "DataHandler",
    "DataHandlerError",
    "DataSourceError",
    "FileValidationError",
    "UnsupportedFormatError", 
    "DataReadError",
    "SchemaError",
    "MetadataError",
    
    # Format handlers
    "ParquetHandler",
    "ParquetHandlerError",
    "JsonHandler",
    "JsonHandlerError",
    "CsvHandler",
    "CsvHandlerError",
]