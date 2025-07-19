"""
Base data handler interface for parqv data sources.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core import get_logger


class DataHandler(ABC):
    """
    Abstract Base Class for data handlers.
    
    Defines the common interface required by the ParqV application
    to interact with different data file formats.
    """

    def __init__(self, file_path: Path):
        """
        Initialize the handler with the file path.
        
        Subclasses should open the file or set up necessary resources here.

        Args:
            file_path: Path to the data file.

        Raises:
            DataHandlerError: If initialization fails (e.g., file not found, format error).
        """
        self.file_path = file_path
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    def close(self) -> None:
        """
        Close any open resources (files, connections, etc.).
        
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def get_metadata_summary(self) -> Dict[str, Any]:
        """
        Get a dictionary containing summary metadata about the data source.
        
        Keys should be human-readable strings. Values can be of various types.
        Should include an 'error' key if metadata retrieval fails.

        Returns:
            A dictionary with metadata summary or an error dictionary.
        """
        pass

    @abstractmethod
    def get_schema_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the schema as a list of dictionaries.
        
        Each dictionary should represent a column and ideally contain keys:
        - 'name' (str): Column name.
        - 'type' (str): Formatted data type string.
        - 'nullable' (Any): Indicator of nullability (e.g., bool, str "YES"/"NO").

        Returns:
            A list of schema dictionaries, an empty list if no columns,
            or None if schema retrieval failed.
        """
        pass

    @abstractmethod
    def get_data_preview(self, num_rows: int = 50) -> Optional[pd.DataFrame]:
        """
        Fetch a preview of the data.

        Args:
            num_rows: The maximum number of rows to fetch.

        Returns:
            A pandas DataFrame with preview data, an empty DataFrame if no data,
            a DataFrame with an 'error' column on failure, or None on critical failure.
        """
        pass

    @abstractmethod
    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        """
        Calculate and return statistics for a specific column.
        
        The returned dictionary should ideally contain keys like:
        - 'column' (str): Column name.
        - 'type' (str): Formatted data type string.
        - 'nullable' (Any): Nullability indicator.
        - 'calculated' (Dict[str, Any]): Dictionary of computed statistics.
        - 'error' (Optional[str]): Error message if calculation failed.
        - 'message' (Optional[str]): Informational message.

        Args:
            column_name: The name of the column.

        Returns:
            A dictionary containing column statistics or error information.
        """
        pass

    def format_size(self, num_bytes: int) -> str:
        """
        Format bytes into a human-readable string.
        
        Args:
            num_bytes: Number of bytes to format
            
        Returns:
            Human-readable size string
        """
        if num_bytes < 1024:
            return f"{num_bytes} bytes"
        elif num_bytes < 1024 ** 2:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 ** 3:
            return f"{num_bytes / 1024 ** 2:.1f} MB"
        else:
            return f"{num_bytes / 1024 ** 3:.1f} GB"

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context related to this object, ensuring cleanup."""
        self.close()

    def __del__(self):
        """Attempt to close the handler when the object is garbage collected (best effort)."""
        try:
            self.close()
        except Exception:
            # Ignore exceptions during garbage collection
            pass
