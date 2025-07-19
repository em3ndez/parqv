"""
Base classes for parqv views.
"""

from typing import Optional

from textual.containers import Container
from textual.widgets import Static

from ..core import get_logger
from ..handlers import DataHandler


class BaseView(Container):
    """
    Base class for all parqv views.
    
    Provides common functionality for data loading, error handling,
    and handler access.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_mounted = False

    @property
    def logger(self):
        """Get a logger for this view."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @property
    def handler(self) -> Optional[DataHandler]:
        """Get the data handler from the app."""
        if hasattr(self.app, 'handler'):
            return self.app.handler
        return None

    def on_mount(self) -> None:
        """Called when the view is mounted."""
        self._is_mounted = True
        self.load_content()

    def load_content(self) -> None:
        """
        Load the main content for this view. Must be implemented by subclasses.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement load_content()")

    def clear_content(self) -> None:
        """Clear all content from the view."""
        try:
            self.query("*").remove()
        except Exception as e:
            self.logger.error(f"Error clearing content: {e}")

    def show_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Display an error message in the view.
        
        Args:
            message: Error message to display
            exception: Optional exception that caused the error
        """
        if exception:
            self.logger.exception(f"Error in {self.__class__.__name__}: {message}")
        else:
            self.logger.error(f"Error in {self.__class__.__name__}: {message}")

        self.clear_content()
        error_widget = Static(f"[red]Error: {message}[/red]", classes="error-content")
        self.mount(error_widget)

    def show_info(self, message: str) -> None:
        """
        Display an informational message in the view.
        
        Args:
            message: Info message to display
        """
        self.logger.info(f"Info in {self.__class__.__name__}: {message}")
        self.clear_content()
        info_widget = Static(f"[blue]Info: {message}[/blue]", classes="info-content")
        self.mount(info_widget)

    def check_handler_available(self) -> bool:
        """
        Check if handler is available and show error if not.
        
        Returns:
            True if handler is available, False otherwise
        """
        if not self.handler:
            self.show_error("Data handler not available")
            return False
        return True
