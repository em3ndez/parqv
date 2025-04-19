import json
import logging
from typing import Dict, Any, Optional, List, Union

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Container
from textual.reactive import var
from textual.widgets import Static, ListView, ListItem, Label, LoadingIndicator

log = logging.getLogger(__name__)


class ColumnListItem(ListItem):
    def __init__(self, column_name: str) -> None:
        super().__init__(Label(column_name), name=column_name, id=f"col-item-{column_name.replace(' ', '_')}")
        self.column_name = column_name


def format_stats_for_display(stats_data: Dict[str, Any]) -> List[Union[str, Text]]:
    if not stats_data:
        return [Text.from_markup("[red]No statistics data available.[/red]")]

    lines: List[Union[str, Text]] = []
    col_name = stats_data.get("column", "N/A")
    col_type = stats_data.get("type", "Unknown")
    nullable = stats_data.get("nullable", "Unknown")

    lines.append(Text.assemble(("Column: ", "bold"), f"`{col_name}`"))
    lines.append(Text.assemble(("Type:   ", "bold"), f"{col_type} ({'Nullable' if nullable else 'Required'})"))
    lines.append("─" * (len(col_name) + len(col_type) + 20))

    calc_error = stats_data.get("error")
    if calc_error:
        lines.append(Text("Calculation Error:", style="bold red"))
        lines.append(f"```{calc_error}```")

    calculated = stats_data.get("calculated")
    if calculated:
        lines.append(Text("Calculated Statistics:", style="bold"))
        keys_to_display = [
            "Total Count", "Valid Count", "Null Count", "Null Percentage",
            "Min", "Max", "Mean", "StdDev", "Distinct Count", "Value Counts"
        ]
        for key in keys_to_display:
            if key in calculated:
                value = calculated[key]
                if isinstance(value, dict):
                    lines.append(f"  - {key}:")
                    for sub_key, sub_val in value.items():
                        lines.append(f"    - {sub_key}: {sub_val:,}")
                else:
                    lines.append(f"  - {key}: {value}")
        lines.append("")

    meta_stats = stats_data.get("basic_metadata_stats")
    if meta_stats:
        lines.append(Text("Stats from File Metadata (Per Row Group):", style="bold"))
        try:
            json_str = json.dumps(meta_stats, indent=2, default=str)
            lines.append(f"```json\n{json_str}\n```")
        except Exception as e:
            lines.append(f"  (Error formatting metadata: {e})")
        lines.append("")

    meta_stats_error = stats_data.get("metadata_stats_error")
    if meta_stats_error:
        lines.append(Text(f"Metadata Stats Warning: {meta_stats_error}", style="yellow"))

    message = stats_data.get("message")
    if message and not calculated:
        lines.append(Text(message, style="italic"))

    return lines


class SchemaView(VerticalScroll):
    DEFAULT_STATS_MESSAGE = "Select a column above to view statistics."
    loading = var(False)

    def compose(self) -> ComposeResult:
        yield ListView(id="column-list-view")
        yield LoadingIndicator(id="schema-loading-indicator")
        yield Container(id="schema-stats-content")

    def on_mount(self) -> None:
        self.query_one("#schema-loading-indicator", LoadingIndicator).styles.display = "none"
        self.call_later(self.load_column_list)
        self.call_later(self._update_stats_display, [])

    def load_column_list(self):
        list_view: Optional[ListView] = None
        try:
            list_views = self.query("#column-list-view")
            if not list_views:
                log.error("ListView widget (#column-list-view) not found!")
                return
            list_view = list_views.first()
            log.debug("ListView widget found.")

            list_view.clear()

            if self.app.handler and self.app.handler.schema:
                column_names: List[str] = self.app.handler.schema.names
                if column_names:
                    for name in column_names:
                        list_view.append(ColumnListItem(name))
                else:
                    log.warning("Schema has no columns.")
                    list_view.append(ListItem(Label("[yellow]Schema has no columns.[/yellow]")))
            elif not self.app.handler:
                log.error("Parquet handler not available.")
                list_view.append(ListItem(Label("[red]Parquet handler not available.[/red]")))
            else:
                log.error("Parquet schema not available.")
                list_view.append(ListItem(Label("[red]Parquet schema not available.[/red]")))

        except Exception as e:
            log.exception("Error loading column list in SchemaView:")
            if list_view:
                list_view.clear()
                list_view.append(ListItem(Label(f"[red]Error loading schema view: {e}[/red]")))

    def watch_loading(self, loading: bool) -> None:
        loading_indicator = self.query_one("#schema-loading-indicator", LoadingIndicator)
        stats_content = self.query_one("#schema-stats-content", Container)
        loading_indicator.styles.display = "block" if loading else "none"
        stats_content.styles.display = "none" if loading else "block"

    async def _update_stats_display(self, lines: List[Union[str, Text]]) -> None:
        try:
            content_area = self.query_one("#schema-stats-content", Container)
            await content_area.query("*").remove()

            if not lines:
                await content_area.mount(Static(self.DEFAULT_STATS_MESSAGE, classes="stats-line"))
                return

            new_widgets: List[Static] = []
            for line in lines:
                content: Union[str, Text] = line
                css_class = "stats-line"
                if isinstance(line, str) and line.startswith("```"):
                    content = line.strip("` \n")
                    css_class = "stats-code"
                elif isinstance(line, Text) and ("red" in str(line.style) or "yellow" in str(line.style)):
                    css_class = "stats-error stats-line"

                new_widgets.append(Static(content, classes=css_class))

            if new_widgets:
                await content_area.mount_all(new_widgets)
        except Exception as e:
            log.error(f"Error updating stats display: {e}", exc_info=True)
            try:
                await content_area.query("*").remove()
                await content_area.mount(Static(f"[red]Internal error displaying stats: {e}[/red]"))
            except Exception:
                pass

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        event.stop()
        selected_item = event.item

        if isinstance(selected_item, ColumnListItem):
            column_name = selected_item.column_name
            log.info(f"Column selected: {column_name}")
            self.loading = True

            stats_data: Dict[str, Any] = {}
            error_str: Optional[str] = None
            try:
                if self.app.handler:
                    stats_data = self.app.handler.get_column_stats(column_name)
                else:
                    error_str = "[red]Error: Parquet handler not available.[/]"
                    log.error("Parquet handler not found on app.")
            except Exception as e:
                log.exception(f"ERROR calculating stats for {column_name}")
                error_str = f"[red]Error loading stats for {column_name}:\n{type(e).__name__}: {e}[/]"

            lines_to_render = format_stats_for_display(stats_data) if not error_str else [Text.from_markup(error_str)]
            await self._update_stats_display(lines_to_render)
            self.loading = False
        else:
            await self._update_stats_display([])
            self.loading = False
