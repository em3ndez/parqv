"""
Schema view for displaying column schema and statistics.
"""

from typing import Dict, Any, Optional, List

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Container, Horizontal
from textual.reactive import var
from textual.widgets import Static, ListView, ListItem, Label, LoadingIndicator

from .base import BaseView
from .utils import format_stats_for_display


class ColumnListItem(ListItem):
    """A ListItem that stores the column name for schema display."""

    def __init__(self, column_name: str) -> None:
        # Ensure IDs are CSS-safe (replace spaces, etc.)
        safe_id_name = "".join(c if c.isalnum() else '_' for c in column_name)
        super().__init__(Label(column_name), name=column_name, id=f"col-item-{safe_id_name}")
        self.column_name = column_name


class SchemaView(BaseView):
    """
    View for displaying schema information and column statistics.
    
    Shows a list of columns on the left and detailed statistics
    for the selected column on the right.
    """

    DEFAULT_STATS_MESSAGE = "Select a column from the list to view its statistics."

    # Reactive variable for loading state
    loading = var(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._columns_data: Optional[List[Dict[str, Any]]] = None
        self._current_column: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the schema view layout."""
        with Horizontal():
            # Left side: Column list
            with Container(id="column-list-container", classes="column-list"):
                yield Static("Columns", classes="section-title")
                yield ListView(id="column-list-view")

            # Right side: Column statistics
            with Container(id="stats-container", classes="column-stats"):
                yield Static("Column Statistics", classes="section-title")
                with VerticalScroll(id="schema-stats-scroll"):
                    yield Container(id="schema-stats-content")
                yield LoadingIndicator(id="schema-loading-indicator")

    def load_content(self) -> None:
        """Load schema content."""
        if not self.check_handler_available():
            return

        try:
            # Load column list
            self._load_column_list()

            # Display default message in stats area
            self._display_default_message()

            self.logger.info("Schema loaded successfully")

        except Exception as e:
            self.show_error("Failed to load schema", e)

    def _load_column_list(self) -> None:
        """Load the list of columns from the data handler."""
        try:
            list_view = self.query_one("#column-list-view", ListView)
            list_view.clear()

            # Get schema data from handler
            self._columns_data = self.handler.get_schema_data()
            self.logger.debug(f"Received schema data: {self._columns_data}")

            if self._columns_data is None:
                self._show_list_error("Could not load schema data")
                return

            if not self._columns_data:
                self._show_list_warning("Schema has no columns")
                return

            # Populate column list
            column_count = 0
            for col_info in self._columns_data:
                column_name = col_info.get("name")
                if column_name:
                    list_view.append(ColumnListItem(column_name))
                    column_count += 1
                else:
                    self.logger.warning("Found column info without a 'name' key")

            self.logger.info(f"Populated column list with {column_count} columns")

        except Exception as e:
            self.logger.exception("Error loading column list")
            self._show_list_error(f"Error loading schema: {e}")

    def _show_list_error(self, message: str) -> None:
        """Show error message in the column list."""
        try:
            list_view = self.query_one("#column-list-view", ListView)
            list_view.clear()
            list_view.append(ListItem(Label(f"[red]{message}[/red]")))
        except Exception as e:
            self.logger.error(f"Failed to show list error: {e}")

    def _show_list_warning(self, message: str) -> None:
        """Show warning message in the column list."""
        try:
            list_view = self.query_one("#column-list-view", ListView)
            list_view.clear()
            list_view.append(ListItem(Label(f"[yellow]{message}[/yellow]")))
        except Exception as e:
            self.logger.error(f"Failed to show list warning: {e}")

    def _display_default_message(self) -> None:
        """Display the initial message in the stats area."""
        try:
            stats_container = self.query_one("#schema-stats-content", Container)
            stats_container.query("*").remove()
            stats_container.mount(Static(self.DEFAULT_STATS_MESSAGE, classes="stats-line"))
        except Exception as e:
            self.logger.error(f"Failed to display default stats message: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle column selection from the list."""
        if hasattr(event.item, 'column_name'):
            column_name = event.item.column_name
            self._current_column = column_name
            self._load_column_stats(column_name)
        else:
            self.logger.warning("Selected item does not have column_name attribute")

    def _load_column_stats(self, column_name: str) -> None:
        """
        Load and display statistics for the selected column.
        
        Args:
            column_name: Name of the column to analyze
        """
        if not self.handler:
            self._show_stats_error("Data handler not available")
            return

        try:
            # Set loading state
            self.loading = True

            # Get column statistics
            self.logger.debug(f"Loading stats for column: {column_name}")
            raw_stats = self.handler.get_column_stats(column_name)

            # Format stats for display
            formatted_lines = format_stats_for_display(raw_stats)

            # Display the formatted stats
            self._display_column_stats(formatted_lines)

        except Exception as e:
            self.logger.exception(f"Error loading stats for column {column_name}")
            self._show_stats_error(f"Failed to load statistics: {e}")
        finally:
            self.loading = False

    def _display_column_stats(self, formatted_lines: List) -> None:
        """
        Display formatted column statistics.
        
        Args:
            formatted_lines: List of formatted text lines to display
        """
        try:
            stats_container = self.query_one("#schema-stats-content", Container)
            stats_container.query("*").remove()

            for line in formatted_lines:
                if isinstance(line, Text):
                    stats_container.mount(Static(line, classes="stats-line"))
                else:
                    stats_container.mount(Static(str(line), classes="stats-line"))

        except Exception as e:
            self.logger.error(f"Failed to display column stats: {e}")
            self._show_stats_error("Failed to display statistics")

    def _show_stats_error(self, message: str) -> None:
        """Show error message in the stats area."""
        try:
            stats_container = self.query_one("#schema-stats-content", Container)
            stats_container.query("*").remove()
            stats_container.mount(Static(f"[red]Error: {message}[/red]", classes="error-content"))
        except Exception as e:
            self.logger.error(f"Failed to show stats error: {e}")

    def watch_loading(self, loading: bool) -> None:
        """React to changes in the loading state."""
        try:
            loading_indicator = self.query_one("#schema-loading-indicator", LoadingIndicator)
            stats_scroll = self.query_one("#schema-stats-scroll", VerticalScroll)

            if loading:
                loading_indicator.display = True
                stats_scroll.display = False
            else:
                loading_indicator.display = False
                stats_scroll.display = True

        except Exception as e:
            self.logger.error(f"Error updating loading state: {e}")

    def refresh_schema(self) -> None:
        """Refresh the schema display."""
        self._current_column = None
        self.clear_content()
        self.load_content()

    def get_current_column(self) -> Optional[str]:
        """Get the currently selected column name."""
        return self._current_column

    def get_columns_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get the current columns data."""
        return self._columns_data
