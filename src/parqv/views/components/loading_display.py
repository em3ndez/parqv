"""
Loading display component for parqv views.
"""

from textual.containers import Center, Middle
from textual.widgets import LoadingIndicator, Label


class LoadingDisplay(Center):
    """
    A reusable component for displaying loading states in a consistent format.
    """
    
    def __init__(self, message: str = "Loading...", **kwargs):
        """
        Initialize the loading display.
        
        Args:
            message: Loading message to display
            **kwargs: Additional arguments for Center container
        """
        super().__init__(**kwargs)
        self.message = message
    
    def compose(self):
        """Compose the loading display layout."""
        with Middle():
            yield LoadingIndicator()
            yield Label(self.message, classes="loading-message")
    
    @classmethod
    def data_loading(cls, **kwargs) -> 'LoadingDisplay':
        """Create a loading display for data loading operations."""
        return cls(message="Loading data...", **kwargs)
    
    @classmethod
    def metadata_loading(cls, **kwargs) -> 'LoadingDisplay':
        """Create a loading display for metadata loading operations."""
        return cls(message="Loading metadata...", **kwargs)
    
    @classmethod
    def schema_loading(cls, **kwargs) -> 'LoadingDisplay':
        """Create a loading display for schema loading operations."""
        return cls(message="Loading schema...", **kwargs) 