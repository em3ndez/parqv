"""
Data view for displaying tabular data preview.
"""

from typing import Optional

import pandas as pd
from textual.app import ComposeResult

from .base import BaseView
from .components import EnhancedDataTable
from ..core import DEFAULT_PREVIEW_ROWS


class DataView(BaseView):
    """
    View for displaying a preview of the data in tabular format.
    
    Shows the first N rows of data in an interactive table format
    with proper error handling and loading states.
    """

    def __init__(self, preview_rows: int = DEFAULT_PREVIEW_ROWS, **kwargs):
        """
        Initialize the data view.
        
        Args:
            preview_rows: Number of rows to show in preview
            **kwargs: Additional arguments for BaseView
        """
        super().__init__(**kwargs)
        self.preview_rows = preview_rows
        self._data_table: Optional[EnhancedDataTable] = None

    def compose(self) -> ComposeResult:
        """Compose the data view layout."""
        self._data_table = EnhancedDataTable(id="data-preview-table")
        yield self._data_table

    def load_content(self) -> None:
        """Load and display data content."""
        if not self.check_handler_available():
            return

        if not self._data_table:
            self.show_error("Data table component not initialized")
            return

        try:
            # Get data preview from handler
            self.logger.info(f"Loading data preview ({self.preview_rows} rows)")
            df = self.handler.get_data_preview(num_rows=self.preview_rows)

            # Validate DataFrame
            if df is None:
                self.show_error("Could not load data preview - handler returned None")
                return

            # Handle error DataFrame (some handlers return error as DataFrame)
            if self._is_error_dataframe(df):
                error_msg = self._extract_error_from_dataframe(df)
                self.show_error(error_msg)
                return

            # Load DataFrame into table
            success = self._data_table.load_dataframe(df, max_rows=self.preview_rows)

            if success:
                self.logger.info(f"Data preview loaded successfully: {len(df)} rows")
            else:
                self.show_error("Failed to load data into table component")

        except Exception as e:
            self.show_error("Failed to load data preview", e)

    def _is_error_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Check if the DataFrame represents an error condition.
        
        Args:
            df: DataFrame to check
            
        Returns:
            True if the DataFrame contains error information
        """
        return (
                not df.empty and
                "error" in df.columns and
                len(df.columns) == 1
        )

    def _extract_error_from_dataframe(self, df: pd.DataFrame) -> str:
        """
        Extract error message from an error DataFrame.
        
        Args:
            df: Error DataFrame
            
        Returns:
            Error message string
        """
        try:
            if not df.empty and "error" in df.columns:
                return str(df["error"].iloc[0])
        except Exception:
            pass
        return "Unknown error in data loading"

    def refresh_data(self) -> None:
        """Refresh the data display."""
        self.clear_content()
        self.load_content()

    def set_preview_rows(self, new_rows: int) -> None:
        """
        Update the number of preview rows and refresh display.
        
        Args:
            new_rows: New number of rows to preview
        """
        if new_rows > 0:
            self.preview_rows = new_rows
            self.refresh_data()
        else:
            self.logger.warning(f"Invalid preview_rows value: {new_rows}")

    def get_current_data(self) -> Optional[pd.DataFrame]:
        """
        Get the currently displayed data if available.
        
        Returns:
            Currently loaded DataFrame or None
        """
        if not self.handler:
            return None

        try:
            return self.handler.get_data_preview(num_rows=self.preview_rows)
        except Exception as e:
            self.logger.error(f"Failed to get current data: {e}")
            return None
