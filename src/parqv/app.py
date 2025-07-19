from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult, Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Static, Label, TabbedContent, TabPane

from .core import CSS_PATH, FileValidationError, validate_and_detect_file, HandlerFactory, HandlerCreationError, get_logger
from .handlers import DataHandler
from .views.data_view import DataView
from .views.metadata_view import MetadataView
from .views.schema_view import SchemaView

log = get_logger(__name__)


class ParqV(App[None]):
    """A Textual app to visualize Parquet or JSON files."""

    CSS_PATH = CSS_PATH
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, file_path_str: Optional[str] = None, *args, **kwargs):
        """
        Initialize the ParqV application.
        
        Args:
            file_path_str: Path to the file to visualize
            *args, **kwargs: Additional arguments for the Textual App
        """
        super().__init__(*args, **kwargs)
        
        # Application state
        self.file_path: Optional[Path] = None
        self.handler: Optional[DataHandler] = None
        self.handler_type: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # Initialize with file if provided
        if file_path_str:
            self._initialize_file_handler(file_path_str)

    def _initialize_file_handler(self, file_path_str: str) -> None:
        """
        Initialize the file handler for the given file path.
        
        Args:
            file_path_str: Path to the file to process
        """
        try:
            # Validate file and detect type
            self.file_path, self.handler_type = validate_and_detect_file(file_path_str)
            
            # Create appropriate handler
            self.handler = HandlerFactory.create_handler(self.file_path, self.handler_type)
            
            log.info(f"Successfully initialized {self.handler_type} handler for: {self.file_path.name}")
            
        except (FileValidationError, HandlerCreationError) as e:
            self.error_message = str(e)
            log.error(f"Failed to initialize handler: {e}")
            
        except Exception as e:
            self.error_message = f"An unexpected error occurred: {e}"
            log.exception("Unexpected error during handler initialization")

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        
        if self.error_message:
            log.debug(f"Displaying error message: {self.error_message}")
            yield Container(
                Label("Error Loading File:", classes="error-title"),
                Static(self.error_message, classes="error-content"),
                id="error-container"
            )
        elif self.handler:
            log.debug(f"Composing main layout with TabbedContent for {self.handler_type} handler.")
            with TabbedContent(id="main-tabs"):
                yield TabPane("Metadata", MetadataView(id="metadata-view"), id="tab-metadata")
                yield TabPane("Schema", SchemaView(id="schema-view"), id="tab-schema")
                yield TabPane("Data Preview", DataView(id="data-view"), id="tab-data")
        else:
            log.warning("No handler available and no error message set")
            yield Container(
                Label("No file loaded.", classes="error-title"),
                Static("Please provide a valid file path.", classes="error-content"),
                id="no-file-container"
            )
            
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount event - set up header information."""
        log.debug("App mounted.")
        self._update_header()

    def _update_header(self) -> None:
        """Update the header with file and format information."""
        try:
            header = self.query_one(Header)
            
            if self.handler and self.file_path and self.handler_type:
                display_name = self.file_path.name
                format_name = self.handler_type.capitalize()
                header.title = f"parqv - {display_name}"
                header.sub_title = f"Format: {format_name}"
            elif self.error_message:
                header.title = "parqv - Error"
                header.sub_title = "Failed to load file"
            else:
                header.title = "parqv"
                header.sub_title = "File Viewer"
                
        except Exception as e:
            log.error(f"Failed to update header: {e}")

    def action_quit(self) -> None:
        """Handle quit action - cleanup and exit."""
        log.info("Quit action triggered.")
        self._cleanup()
        self.exit()

    def _cleanup(self) -> None:
        """Clean up resources before exit."""
        if self.handler:
            try:
                self.handler.close()
                log.info("Handler closed successfully.")
            except Exception as e:
                log.error(f"Error during handler cleanup: {e}")


# For backward compatibility, keep the old CLI entry point
def run_app():
    """
    Legacy CLI entry point for backward compatibility.
    
    Note: New code should use parqv.cli.run_app() instead.
    """
    from .cli import run_app as new_run_app
    log.warning("Using legacy run_app(). Consider importing from parqv.cli instead.")
    new_run_app()


if __name__ == "__main__":
    run_app()
