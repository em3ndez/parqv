"""
Handler factory for creating appropriate data handlers based on file type.
"""

from pathlib import Path
from typing import Optional

from ..handlers import DataHandler, DataHandlerError, ParquetHandler, JsonHandler
from .logging import get_logger

log = get_logger(__name__)


class HandlerCreationError(Exception):
    """Exception raised when handler creation fails."""
    pass


class HandlerFactory:
    """Factory class for creating data handlers."""
    
    # Registry of handler types to handler classes
    _HANDLER_REGISTRY = {
        "parquet": ParquetHandler,
        "json": JsonHandler,
    }
    
    @classmethod
    def create_handler(cls, file_path: Path, handler_type: str) -> DataHandler:
        """
        Creates an appropriate handler for the given file type.
        
        Args:
            file_path: Path to the data file
            handler_type: Type of handler to create ('parquet' or 'json')
            
        Returns:
            An instance of the appropriate DataHandler subclass
            
        Raises:
            HandlerCreationError: If handler creation fails
        """
        if handler_type not in cls._HANDLER_REGISTRY:
            available_types = ", ".join(cls._HANDLER_REGISTRY.keys())
            raise HandlerCreationError(
                f"Unknown handler type: '{handler_type}'. "
                f"Available types: {available_types}"
            )
        
        handler_class = cls._HANDLER_REGISTRY[handler_type]
        
        log.info(f"Creating {handler_type.capitalize()} handler for: {file_path}")
        
        try:
            handler = handler_class(file_path)
            log.info(f"{handler_type.capitalize()} handler created successfully.")
            return handler
            
        except DataHandlerError as e:
            log.error(f"Failed to create {handler_type} handler: {e}")
            raise HandlerCreationError(f"Failed to initialize {handler_type} handler: {e}") from e
            
        except Exception as e:
            log.exception(f"Unexpected error creating {handler_type} handler")
            raise HandlerCreationError(
                f"Unexpected error during {handler_type} handler creation: {e}"
            ) from e
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Returns a list of supported handler types.
        
        Returns:
            List of supported handler type strings
        """
        return list(cls._HANDLER_REGISTRY.keys())
    
    @classmethod
    def register_handler(cls, handler_type: str, handler_class: type[DataHandler]) -> None:
        """
        Registers a new handler type (for extensibility).
        
        Args:
            handler_type: String identifier for the handler type
            handler_class: Class that implements DataHandler interface
        """
        log.info(f"Registering handler type '{handler_type}' with class {handler_class.__name__}")
        cls._HANDLER_REGISTRY[handler_type] = handler_class 