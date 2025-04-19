import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from textual.app import App, ComposeResult, Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Static, Label, TabbedContent, TabPane

from .parquet_handler import ParquetHandler, ParquetHandlerError
from .views.metadata_view import MetadataView
from .views.schema_view import SchemaView
from .views.data_view import DataView
from .views.row_group_view import RowGroupView

LOG_FILENAME = "parqv.log"
file_handler = RotatingFileHandler(
    LOG_FILENAME, maxBytes=1024 * 1024 * 5, backupCount=3, encoding="utf-8"
)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-5.5s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
    handlers=[file_handler], # Log to file
)

log = logging.getLogger(__name__)


class ParqV(App[None]):
    """A Textual app to visualize Parquet files."""

    CSS_PATH = "parqv.css"
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    # App State
    file_path: Optional[Path] = None
    handler: Optional[ParquetHandler] = None
    error_message: Optional[str] = None

    def __init__(self, file_path_str: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.info("Initializing ParqVApp...")
        if file_path_str:
            self.file_path = Path(file_path_str)
            log.info(f"Attempting to load file: {self.file_path}")
            try:
                # Initialize the Parquet handler on app start
                self.handler = ParquetHandler(self.file_path)
                log.info("Parquet handler initialized successfully.")
            except ParquetHandlerError as e:
                self.error_message = str(e)
                log.error(f"Failed to initialize handler: {e}", exc_info=True)
            except Exception as e:
                self.error_message = (
                    f"An unexpected error occurred during initialization: {e}"
                )
                log.exception("Unexpected error during app initialization:")

    def compose(self) -> ComposeResult:
        yield Header()

        if self.error_message:
            log.error(f"Displaying error message: {self.error_message}")
            yield Container(
                Label("Error Loading File:", classes="error-title"),
                Static(self.error_message, classes="error-content"),
            )
        elif self.handler:
            log.debug("Composing main layout with TabbedContent.")
            with TabbedContent(id="main-tabs"):
                with TabPane("Metadata", id="tab-metadata"):
                    yield MetadataView(id="metadata-view")
                with TabPane("Schema", id="tab-schema"):
                    yield SchemaView(id="schema-view")
                with TabPane("Data Preview", id="tab-data"):
                    yield DataView(id="data-view")
                with TabPane("Row Groups", id="tab-rowgroups"):
                    yield RowGroupView(id="rowgroup-view")
        else:
            log.warning("No handler available, showing 'no file' message.")
            yield Container(Label("No file loaded or handler initialization failed."))

        yield Footer()

    def on_mount(self) -> None:
        log.debug("App mounted.")
        try:
            header = self.query_one(Header)
            if self.handler and self.file_path:
                header.title = f"parqv - {self.file_path.name}"
            elif self.error_message:
                header.title = "parqv - Error"
            else:
                header.title = "parqv"
        except Exception as e:
            log.error(f"Failed to set header title: {e}")


    def action_quit(self) -> None:
        log.info("Quit action triggered.")
        self.exit()


# CLI Entry Point
def run_app():
    log.info("--- parqv started ---")
    if len(sys.argv) < 2:
        print("Usage: parqv <path_to_parquet_file>")
        log.error("No file path provided.")
        sys.exit(1)

    file_path_str = sys.argv[1]
    file_path = Path(file_path_str)
    log.debug(f"File path from argument: {file_path}")

    # Basic file validation
    if not file_path.is_file():
        print(f"Error: Path is not a file or does not exist: {file_path}")
        log.error(f"Invalid file path provided: {file_path}")
        sys.exit(1)

    app = ParqV(file_path_str=file_path_str)
    app.run()
    log.info("--- parqv finished ---")


if __name__ == "__main__":
    run_app()