import logging
from typing import Dict, Any, Optional, List, Union

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Container
from textual.reactive import var
from textual.widgets import Static, ListView, ListItem, Label, LoadingIndicator

log = logging.getLogger(__name__)


class ColumnListItem(ListItem):
    """A ListItem that stores the column name."""

    def __init__(self, column_name: str) -> None:
        # Ensure IDs are CSS-safe (replace spaces, etc.)
        safe_id_name = "".join(c if c.isalnum() else '_' for c in column_name)
        super().__init__(Label(column_name), name=column_name, id=f"col-item-{safe_id_name}")
        self.column_name = column_name


def format_stats_for_display(stats_data: Dict[str, Any]) -> List[Union[str, Text]]:
    """Formats the statistics dictionary for display as lines of text."""
    if not stats_data:
        return [Text.from_markup("[red]No statistics data available.[/red]")]

    lines: List[Union[str, Text]] = []
    col_name = stats_data.get("column", "N/A")
    col_type = stats_data.get("type", "Unknown")
    nullable_val = stats_data.get("nullable")

    if nullable_val is True:
        nullable_str = "Nullable"
    elif nullable_val is False:
        nullable_str = "Required"
    else:
        nullable_str = "Unknown Nullability"
    lines.append(Text.assemble(("Column: ", "bold"), f"`{col_name}`"))
    lines.append(Text.assemble(("Type:   ", "bold"), f"{col_type} ({nullable_str})"))
    lines.append("─" * (len(col_name) + len(col_type) + 20))

    calc_error = stats_data.get("error")
    if calc_error:
        lines.append(Text("Calculation Error:", style="bold red"))
        lines.append(f"```\n{calc_error}\n```")
        lines.append("")

    message = stats_data.get("message")
    if message:
        lines.append(Text(f"Info: {message}", style="italic cyan"))
        lines.append("")

    calculated = stats_data.get("calculated")
    if calculated:
        lines.append(Text("Calculated Statistics:", style="bold"))
        keys_to_display = [
            "Total Count", "Valid Count", "Null Count", "Null Percentage",
            "Min", "Max", "Mean", "StdDev", "Variance",
            "Distinct Count", "Min Length", "Max Length", "Avg Length",
            "Value Counts"
        ]
        found_stats = False
        for key in keys_to_display:
            if key in calculated:
                found_stats = True
                value = calculated[key]
                if key == "Value Counts" and isinstance(value, dict):
                    lines.append(f"  - {key}:")
                    for sub_key, sub_val in value.items():
                        sub_val_str = f"{sub_val:,}" if isinstance(sub_val, (int, float)) else str(sub_val)
                        lines.append(f"    - {sub_key}: {sub_val_str}")
                elif isinstance(value, (int, float)):
                    lines.append(f"  - {key}: {value:,}")
                else:
                    lines.append(f"  - {key}: {value}")
        if not found_stats and not calc_error:
            lines.append(Text("  (No specific stats calculated for this type)", style="dim"))
    return lines


class SchemaView(VerticalScroll):
    """Displays a list of columns and the statistics for the selected column."""
    DEFAULT_STATS_MESSAGE = "Select a column from the list above to view its statistics."
    loading = var(False)

    def compose(self) -> ComposeResult:
        """Create child widgets for the SchemaView."""
        yield ListView(id="column-list-view")
        yield LoadingIndicator(id="schema-loading-indicator")
        yield VerticalScroll(Container(id="schema-stats-content"), id="schema-stats-scroll")

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.query_one("#schema-loading-indicator", LoadingIndicator).display = False
        self.query_one("#schema-stats-content", Container).display = False
        self.call_later(self.load_column_list)
        self.call_later(self._display_default_message)

    def _display_default_message(self):
        """Helper to display the initial message in the stats area."""
        try:
            stats_container = self.query_one("#schema-stats-content", Container)
            stats_container.query("*").remove()
            stats_container.mount(Static(self.DEFAULT_STATS_MESSAGE, classes="stats-line"))
            stats_container.display = True
        except Exception as e:
            log.error(f"Failed to display default stats message: {e}")

    def load_column_list(self):
        """Loads the list of columns from the data handler."""
        list_view: Optional[ListView] = self.query_one("#column-list-view", ListView)
        list_view.clear()

        try:
            if not self.app.handler:
                log.error("SchemaView: Data handler not available.")
                list_view.append(ListItem(Label("[red]Data handler not available.[/red]")))
                return

            schema_data: Optional[List[Dict[str, str]]] = self.app.handler.get_schema_data()
            log.debug(f"SchemaView: Received schema data for list: {schema_data}")

            if schema_data is None:
                log.error("SchemaView: Failed to retrieve schema data (handler returned None).")
                list_view.append(ListItem(Label("[red]Could not load schema.[/red]")))
            elif not schema_data:
                log.warning("SchemaView: Schema has no columns.")
                list_view.append(ListItem(Label("[yellow]Schema has no columns.[/yellow]")))
            else:
                column_count = 0
                for col_info in schema_data:
                    column_name = col_info.get("name")
                    if column_name:
                        list_view.append(ColumnListItem(column_name))
                        column_count += 1
                    else:
                        log.warning("SchemaView: Found column info without a 'name' key.")
                log.info(f"SchemaView: Populated column list with {column_count} columns.")

        except Exception as e:
            log.exception("Error loading column list in SchemaView:")
            list_view.clear()
            list_view.append(ListItem(Label(f"[red]Error loading schema: {e}[/red]")))

    def watch_loading(self, loading: bool) -> None:
        """React to changes in the loading state."""
        try:
            loading_indicator = self.query_one("#schema-loading-indicator", LoadingIndicator)
            stats_scroll = self.query_one("#schema-stats-scroll", VerticalScroll)
            loading_indicator.display = loading
            stats_scroll.display = not loading
            if loading:
                stats_content = self.query_one("#schema-stats-content", Container)
                stats_content.display = False
        except Exception as e:
            log.error(f"Error updating loading display: {e}")

    async def _update_stats_display(self, lines: List[Union[str, Text]]) -> None:
        """Updates the statistics display area with formatted lines."""
        try:
            stats_content_container = self.query_one("#schema-stats-content", Container)
            stats_scroll_container = self.query_one("#schema-stats-scroll", VerticalScroll)
            await stats_content_container.query("*").remove()

            if not lines:
                await stats_content_container.mount(Static(self.DEFAULT_STATS_MESSAGE, classes="stats-line"))
            else:
                new_widgets: List[Static] = []
                for line in lines:
                    content: Union[str, Text] = line
                    css_class = "stats-line"
                    if isinstance(line, str) and line.startswith("```"):
                        content = line.strip()
                        if content.startswith("```json"):
                            content = content[7:]
                        elif content.startswith("```"):
                            content = content[3:]
                        if content.endswith("```"):
                            content = content[:-3]
                        content = content.strip()
                        css_class = "stats-code"
                    elif isinstance(line, Text):
                        style_str = str(line.style).lower()
                        if "red" in style_str:
                            css_class = "stats-error stats-line"
                        elif "yellow" in style_str:
                            css_class = "stats-warning stats-line"
                        elif "italic" in style_str:
                            css_class = "stats-info stats-line"
                        elif "bold" in style_str:
                            css_class = "stats-header stats-line"
                    new_widgets.append(Static(content, classes=css_class))
                if new_widgets:
                    await stats_content_container.mount_all(new_widgets)

            stats_content_container.display = True
            stats_scroll_container.display = True
            stats_scroll_container.scroll_home(animate=False)
        except Exception as e:
            log.error(f"Error updating stats display: {e}", exc_info=True)
            try:
                await stats_content_container.query("*").remove()
                await stats_content_container.mount(Static(f"[red]Internal error displaying stats: {e}[/red]"))
                stats_content_container.display = True
                stats_scroll_container.display = True
            except Exception:
                pass

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle column selection in the ListView."""
        event.stop()
        selected_item = event.item

        if isinstance(selected_item, ColumnListItem):
            column_name = selected_item.column_name
            self.loading = True

            stats_data: Dict[str, Any] = {}
            error_markup: Optional[str] = None

            try:
                if self.app.handler:
                    stats_data = self.app.handler.get_column_stats(column_name)
                    if stats_data.get("error"):
                        log.warning(f"Handler returned error for column '{column_name}': {stats_data['error']}")
                        error_markup = f"[red]Error getting stats: {stats_data['error']}[/]"
                        stats_data = {}
                else:
                    error_markup = "[red]Error: Data handler not available.[/]"
                    log.error("SchemaView: Data handler not found on app.")
            except Exception as e:
                log.exception(f"Exception calculating stats for {column_name}")
                error_markup = f"[red]Error loading stats for '{column_name}':\n{type(e).__name__}: {e}[/]"

            if error_markup:
                lines_to_render = [Text.from_markup(error_markup)]
            else:
                lines_to_render = format_stats_for_display(stats_data)

            await self._update_stats_display(lines_to_render)
            self.loading = False
        else:
            log.debug("Non-column item selected in ListView.")
            await self._update_stats_display([])
            self.loading = False
