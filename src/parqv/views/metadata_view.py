"""
Metadata view for displaying file metadata information.
"""

from textual.containers import VerticalScroll
from textual.widgets import Pretty

from .base import BaseView
from .components import ErrorDisplay
from .utils import format_metadata_for_display


class MetadataView(BaseView):
    """
    View for displaying metadata information about the loaded file.
    
    Shows file statistics, format information, and other metadata
    in a formatted display.
    """
    
    def load_content(self) -> None:
        """Load and display metadata content."""
        if not self.check_handler_available():
            return
        
        try:
            # Get raw metadata from handler
            raw_metadata = self.handler.get_metadata_summary()
            
            # Format metadata for display
            formatted_metadata = format_metadata_for_display(raw_metadata)
            
            # Check if there's an error in the formatted data
            if "Error" in formatted_metadata and len(formatted_metadata) == 1:
                self.show_error(formatted_metadata["Error"])
                return
            
            # Display the formatted metadata
            self._display_metadata(formatted_metadata)
            
            self.logger.info("Metadata loaded successfully")
            
        except Exception as e:
            self.show_error("Failed to load metadata", e)
    
    def _display_metadata(self, metadata: dict) -> None:
        """
        Display the formatted metadata using Pretty widget.
        
        Args:
            metadata: Formatted metadata dictionary
        """
        try:
            pretty_widget = Pretty(metadata, id="metadata-pretty")
            self.mount(pretty_widget)
        except Exception as e:
            self.logger.error(f"Failed to create Pretty widget: {e}")
            self.show_error("Failed to display metadata")
    
    def refresh_metadata(self) -> None:
        """Refresh the metadata display."""
        self.clear_content()
        self.load_content()