from textual.containers import VerticalScroll
from textual.widgets import DataTable, Static


class RowGroupView(VerticalScroll):

    def on_mount(self) -> None:
        self.load_row_groups()

    def load_row_groups(self):
        try:
            if self.app.handler:
                rg_info_list = self.app.handler.get_row_group_info()

                if rg_info_list:
                    table = DataTable(id="rowgroup-table")
                    table.cursor_type = "row"

                    columns = list(rg_info_list[0].keys())
                    table.add_columns(*columns)

                    rows_data = [
                        tuple(str(rg.get(col, '')) for col in columns)
                        for rg in rg_info_list
                    ]
                    table.add_rows(rows_data)
                    self.mount(table)
                else:
                    self.mount(Static("No row group information available or file has no row groups."))
            else:
                self.mount(Static("Parquet handler not available.", classes="error-content"))
        except Exception as e:
            self.mount(Static(f"Error loading row group info: {e}", classes="error-content"))
