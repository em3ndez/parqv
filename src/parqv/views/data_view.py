import logging
from typing import Optional

import pandas as pd
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

log = logging.getLogger(__name__)


class DataView(Container):
    DEFAULT_ROWS = 50

    def compose(self) -> ComposeResult:
        yield DataTable(id="data-table")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self):
        table: Optional[DataTable] = self.query_one("#data-table", DataTable)

        try:
            table.clear(columns=True)
        except Exception as e:
            log.error(f"Error clearing DataTable: {e}")
            try:
                table.remove()
                table = DataTable(id="data-table")
                self.mount(table)
            except Exception as remount_e:
                log.error(f"Failed to remount DataTable: {remount_e}")
                self.mount(Static("[red]Error initializing data table.[/red]", classes="error-content"))
                return

        try:
            if not self.app.handler:
                self.mount(Static("Parquet handler not available.", classes="error-content"))
                return

            df: Optional[pd.DataFrame] = self.app.handler.get_data_preview(num_rows=self.DEFAULT_ROWS)

            if df is None:
                self.mount(Static("Could not load data preview."))
                return

            if df.empty:
                self.mount(Static("No data in the preview range or file is empty."))
                return

            table.cursor_type = "row"
            columns = [str(col) for col in df.columns]
            table.add_columns(*columns)
            rows_data = [
                tuple(str(item) if pd.notna(item) else "" for item in row)
                for row in df.itertuples(index=False, name=None)
            ]
            table.add_rows(rows_data)
            log.info("DataTable populated successfully.")

        except Exception as e:
            log.exception("Error loading data preview in DataView:")
            try:
                self.query("DataTable, Static").remove()
                self.mount(Static(f"Error loading data preview: {e}", classes="error-content"))
            except Exception as display_e:
                log.error(f"Error displaying error message: {display_e}")
