import logging
from textual.containers import VerticalScroll
from textual.widgets import Static, Pretty

log = logging.getLogger(__name__)

class MetadataView(VerticalScroll):

    def on_mount(self) -> None:
        self.load_metadata()

    def load_metadata(self):
        self.query("*").remove()
        try:
            if self.app.handler:
                meta_data = self.app.handler.get_metadata_summary()
                if meta_data.get("error"):
                     self.mount(Static(f"[red]Error getting metadata: {meta_data['error']}[/red]", classes="error-content"))
                else:
                     pretty_widget = Pretty(meta_data)
                     self.mount(pretty_widget)
            else:
                self.mount(Static("[red]Data handler not available.[/red]", classes="error-content"))
        except Exception as e:
            log.exception("Error loading metadata view")
            self.mount(Static(f"[red]Error loading metadata: {e}[/red]", classes="error-content"))