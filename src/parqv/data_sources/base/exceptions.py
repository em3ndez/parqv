"""
Exception classes for data sources.
"""


class DataSourceError(Exception):
    """Base exception for all data source errors."""
    pass


class DataHandlerError(DataSourceError):
    """Base exception for all data handler errors."""
    pass


class FileValidationError(DataSourceError):
    """Exception raised when file validation fails."""
    pass


class UnsupportedFormatError(DataSourceError):
    """Exception raised when an unsupported file format is encountered."""
    pass


class DataReadError(DataSourceError):
    """Exception raised when data reading fails."""
    pass


class SchemaError(DataSourceError):
    """Exception raised when schema operations fail."""
    pass


class MetadataError(DataSourceError):
    """Exception raised when metadata operations fail."""
    pass 