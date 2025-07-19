import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Type

from textual.app import App, ComposeResult, Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Static, Label, TabbedContent, TabPane

from .handlers import (
    DataHandler,
    DataHandlerError,
    ParquetHandler,
    JsonHandler,
)
from .views.data_view import DataView
from .views.metadata_view import MetadataView
from .views.schema_view import SchemaView

LOG_FILENAME = "parqv.log"
file_handler = RotatingFileHandler(
    LOG_FILENAME, maxBytes=1024 * 1024 * 5, backupCount=3, encoding="utf-8"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5.5s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
    handlers=[file_handler, logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

AnyHandler = DataHandler
AnyHandlerError = DataHandlerError


class ParqV(App[None]):
    """A Textual app to visualize Parquet or JSON files."""

    CSS_PATH = "parqv.css"
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    # App State
    file_path: Optional[Path] = None
    handler: Optional[AnyHandler] = None  # Use ABC type hint
    handler_type: Optional[str] = None  # Keep for display ('parquet', 'json')
    error_message: Optional[str] = None

    def __init__(self, file_path_str: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not file_path_str:
            self.error_message = "No file path provided."
            log.error(self.error_message)
            return

        self.file_path = Path(file_path_str)
        log.debug(f"Input file path: {self.file_path}")

        if not self.file_path.is_file():
            self.error_message = f"File not found or is not a regular file: {self.file_path}"
            log.error(self.error_message)
            return

        file_suffix = self.file_path.suffix.lower()

        if file_suffix == ".parquet":
            log.info("Detected '.parquet' extension, using ParquetHandler.")
            handler_class = ParquetHandler
            detected_type = "parquet"
        elif file_suffix in [".json", ".ndjson"]:
            log.info(f"Detected '{file_suffix}' extension, using JsonHandler.")
            handler_class = JsonHandler
            detected_type = "json"
        else:
            self.error_message = f"Unsupported file extension: '{file_suffix}'. Only .parquet, .json, .ndjson are supported."
            log.error(self.error_message)
            return

        # Instantiate Handler
        if handler_class:
            log.info(f"Attempting to initialize {detected_type.capitalize()} handler for: {self.file_path}")
            try:
                self.handler = handler_class(self.file_path)
                self.handler_type = detected_type
                log.info(f"{detected_type.capitalize()} handler initialized successfully.")
            except DataHandlerError as e:
                self.error_message = f"Failed to initialize {detected_type} handler: {e}"
                log.error(self.error_message, exc_info=True)
            except Exception as e:
                self.error_message = f"An unexpected error occurred during {detected_type} handler initialization: {e}"
                log.exception(f"Unexpected error during {detected_type} handler initialization:")

    def compose(self) -> ComposeResult:
        yield Header()
        if self.error_message:
            log.error(f"Displaying error message: {self.error_message}")
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
            log.error("Compose called but no handler and no error message. Initialization likely failed silently.")
            yield Container(Label("Initialization failed."), id="init-failed")
        yield Footer()

    def on_mount(self) -> None:
        log.debug("App mounted.")
        try:
            header = self.query_one(Header)
            if self.handler and self.file_path:
                display_name = self.file_path.name
                format_name = self.handler_type.capitalize() if self.handler_type else "Unknown"
                header.title = f"parqv - {display_name}"
                header.sub_title = f"Format: {format_name}"
            elif self.error_message:
                header.title = "parqv - Error"
            else:
                header.title = "parqv"
        except Exception as e:
            log.error(f"Failed to set header title: {e}")

    def action_quit(self) -> None:
        log.info("Quit action triggered.")
        if self.handler:
            try:
                self.handler.close()
            except Exception as e:
                log.error(f"Error during handler cleanup: {e}")
        self.exit()


# CLI Entry Point
def run_app():
    log.info("--- parqv (ABC Handler) started ---")
    if len(sys.argv) < 2:
        log.info("Usage: parqv <path_to_parquet_or_json_file>")
        log.error("No file path provided.")
        sys.exit(1)

    file_path_str = sys.argv[1]
    log.debug(f"File path from argument: {file_path_str}")

    _path = Path(file_path_str)
    if not _path.suffix.lower() in ['.parquet', '.json', '.ndjson']:
        log.error(f"Error: Unsupported file type '{_path.suffix}'. Please provide a .parquet, .json, or .ndjson file.")
        log.error(f"Unsupported file type provided via CLI: {_path.suffix}")
        sys.exit(1)

    app = ParqV(file_path_str=file_path_str)
    app.run()


if __name__ == "__main__":
    run_app()
