from textual.containers import VerticalScroll
from textual.widgets import Static, Pretty


class MetadataView(VerticalScroll):

    def on_mount(self) -> None:
        self.load_metadata()

    def load_metadata(self):
        try:
            if self.app.handler:
                meta_data = self.app.handler.get_metadata_summary()
                pretty_widget = Pretty(meta_data)
                self.mount(pretty_widget)
            else:
                self.mount(Static("Parquet handler not available.", classes="error-content"))
        except Exception as e:
            self.mount(Static(f"Error loading metadata: {e}", classes="error-content"))
