"""
Error display component for parqv views.
"""

from typing import Optional

from textual.containers import VerticalScroll
from textual.widgets import Static, Label


class ErrorDisplay(VerticalScroll):
    """
    A reusable component for displaying error messages in a consistent format.
    """
    
    def __init__(self, 
                 title: str = "Error", 
                 message: str = "An error occurred",
                 details: Optional[str] = None,
                 **kwargs):
        """
        Initialize the error display.
        
        Args:
            title: Error title/category
            message: Main error message
            details: Optional detailed error information
            **kwargs: Additional arguments for VerticalScroll
        """
        super().__init__(**kwargs)
        self.title = title
        self.message = message
        self.details = details
    
    def compose(self):
        """Compose the error display layout."""
        yield Label(self.title, classes="error-title")
        yield Static(f"[red]{self.message}[/red]", classes="error-content")
        
        if self.details:
            yield Static("Details:", classes="error-details-label")
            yield Static(f"[dim]{self.details}[/dim]", classes="error-details")
    
    @classmethod
    def file_not_found(cls, file_path: str, **kwargs) -> 'ErrorDisplay':
        """Create an error display for file not found errors."""
        return cls(
            title="File Not Found",
            message=f"Could not find file: {file_path}",
            details="Please check that the file path is correct and the file exists.",
            **kwargs
        )
    
    @classmethod
    def handler_not_available(cls, **kwargs) -> 'ErrorDisplay':
        """Create an error display for missing data handler."""
        return cls(
            title="Data Handler Not Available",
            message="No data handler is currently loaded",
            details="This usually means the file could not be processed or loaded.",
            **kwargs
        )
    
    @classmethod
    def data_loading_error(cls, error_msg: str, **kwargs) -> 'ErrorDisplay':
        """Create an error display for data loading errors."""
        return cls(
            title="Data Loading Error",
            message="Failed to load data from the file",
            details=f"Technical details: {error_msg}",
            **kwargs
        ) 