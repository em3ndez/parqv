"""
Enhanced data table component for parqv views.
"""

from typing import Optional, List, Tuple, Any

import pandas as pd
from textual.containers import Container
from textual.widgets import DataTable, Static

from ...core import get_logger

log = get_logger(__name__)


class EnhancedDataTable(Container):
    """
    An enhanced data table component that handles DataFrame display with better error handling.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._table: Optional[DataTable] = None
    
    def compose(self):
        """Compose the data table layout."""
        self._table = DataTable(id="enhanced-data-table")
        self._table.cursor_type = "row"
        yield self._table
    
    def clear_table(self) -> bool:
        """
        Clear the table contents safely.
        
        Returns:
            True if cleared successfully, False if recreation was needed
        """
        if not self._table:
            return False
            
        try:
            self._table.clear(columns=True)
            return True
        except Exception as e:
            log.warning(f"Failed to clear table, recreating: {e}")
            return self._recreate_table()
    
    def _recreate_table(self) -> bool:
        """
        Recreate the table if clearing failed.
        
        Returns:
            True if recreation was successful, False otherwise
        """
        try:
            if self._table:
                self._table.remove()
            
            self._table = DataTable(id="enhanced-data-table")
            self._table.cursor_type = "row"
            self.mount(self._table)
            return True
        except Exception as e:
            log.error(f"Failed to recreate table: {e}")
            return False
    
    def load_dataframe(self, df: pd.DataFrame, max_rows: Optional[int] = None) -> bool:
        """
        Load a pandas DataFrame into the table.
        
        Args:
            df: The DataFrame to load
            max_rows: Optional maximum number of rows to display
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._table:
            log.error("Table not initialized")
            return False
        
        try:
            # Clear existing content
            if not self.clear_table():
                return False
            
            # Handle empty DataFrame
            if df.empty:
                self._show_empty_message()
                return True
            
            # Limit rows if specified
            display_df = df.head(max_rows) if max_rows else df
            
            # Add columns
            columns = [str(col) for col in display_df.columns]
            self._table.add_columns(*columns)
            
            # Add rows
            rows_data = self._prepare_rows_data(display_df)
            self._table.add_rows(rows_data)
            
            log.info(f"Loaded {len(display_df)} rows and {len(columns)} columns into table")
            return True
            
        except Exception as e:
            log.exception(f"Error loading DataFrame into table: {e}")
            self._show_error_message(f"Failed to load data: {e}")
            return False
    
    def _prepare_rows_data(self, df: pd.DataFrame) -> List[Tuple[str, ...]]:
        """
        Prepare DataFrame rows for the DataTable.
        
        Args:
            df: The DataFrame to process
            
        Returns:
            List of tuples representing table rows
        """
        rows_data = []
        for row in df.itertuples(index=False, name=None):
            # Convert each item to string, handling NaN values
            row_strings = tuple(
                str(item) if pd.notna(item) else "" 
                for item in row
            )
            rows_data.append(row_strings)
        return rows_data
    
    def _show_empty_message(self) -> None:
        """Show a message when the DataFrame is empty."""
        try:
            self.query("Static").remove()  # Remove any existing messages
            empty_msg = Static("No data available in the selected range or file is empty.", 
                             classes="info-content")
            self.mount(empty_msg)
        except Exception as e:
            log.error(f"Failed to show empty message: {e}")
    
    def _show_error_message(self, message: str) -> None:
        """Show an error message in the table area."""
        try:
            self.query("DataTable, Static").remove()  # Remove table and any messages
            error_msg = Static(f"[red]{message}[/red]", classes="error-content")
            self.mount(error_msg)
        except Exception as e:
            log.error(f"Failed to show error message: {e}")
    
    def get_table(self) -> Optional[DataTable]:
        """Get the underlying DataTable widget."""
        return self._table 