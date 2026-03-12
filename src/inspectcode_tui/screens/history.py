"""History-Screen fuer InspectCode TUI.

Zeigt eine Liste vergangener Scans und ermoeglicht die Wiederholung
eines ausgewaehlten Scans.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ..i18n import t
from ..models.history import History, HistoryEntry


class HistoryScreen(ModalScreen[HistoryEntry | None]):
    """Modal-Dialog zur Anzeige und Auswahl vergangener Scans.

    Gibt den ausgewaehlten HistoryEntry per dismiss() zurueck
    oder None wenn der Dialog ohne Auswahl geschlossen wird.
    """

    DEFAULT_CSS = """
    HistoryScreen {
        align: center middle;
    }

    HistoryScreen > Vertical {
        width: 110;
        height: 35;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    HistoryScreen #history-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    HistoryScreen #history-empty {
        height: auto;
        padding: 2 4;
        content-align: center middle;
        color: $text-muted;
        text-style: italic;
    }

    HistoryScreen #history-table {
        height: 1fr;
    }

    HistoryScreen #history-footer {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "placeholder"),
        Binding("q", "close", "placeholder"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._entries: list[HistoryEntry] = []
        self._init_bindings()

    def _init_bindings(self) -> None:
        """Ersetzt die Platzhalter-Labels der Bindings."""
        import dataclasses
        for key, bindings_list in self._bindings.key_to_bindings.items():
            for i, binding in enumerate(bindings_list):
                if binding.action == "close":
                    self._bindings.key_to_bindings[key][i] = dataclasses.replace(
                        binding, description=t("binding.close")
                    )

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        self._entries = History.load()

        with Vertical():
            yield Static(t("history.title"), id="history-title")

            if not self._entries:
                yield Static(
                    t("history.empty"),
                    id="history-empty",
                )
            else:
                table = DataTable(id="history-table", cursor_type="row")
                table.add_columns(
                    t("history.col_number"),
                    t("history.col_date"),
                    t("history.col_solution"),
                    t("history.col_params"),
                )
                for idx, entry in enumerate(self._entries, start=1):
                    # Datum kuerzen
                    date_str = entry.timestamp[:16].replace("T", " ") if entry.timestamp else "?"

                    # Solution-Name extrahieren
                    sol_name = Path(entry.solution_path).name if entry.solution_path else "?"

                    # Parameter kompakt zusammenbauen
                    params = []
                    if entry.project:
                        params.append(f"--project {entry.project}")
                    if entry.severity != "WARNING":
                        params.append(f"--severity {entry.severity}")
                    if not entry.no_build:
                        params.append("--build")
                    if entry.commit:
                        params.append(f"--commit {entry.commit}")
                    param_str = "  ".join(params) if params else "-"

                    table.add_row(str(idx), date_str, sol_name, param_str, key=str(idx))

                yield table

            yield Static(t("history.footer"), id="history-footer")

    def on_mount(self) -> None:
        """Fokussiert die Tabelle nach dem Oeffnen."""
        if self._entries:
            try:
                table = self.query_one("#history-table", DataTable)
                table.focus()
            except Exception:
                pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Verarbeitet die Auswahl einer Zeile.

        Args:
            event: Das RowSelected-Event mit dem Key der Zeile.
        """
        try:
            idx = int(str(event.row_key.value)) - 1
            if 0 <= idx < len(self._entries):
                self.dismiss(self._entries[idx])
        except (ValueError, IndexError):
            pass

    def action_close(self) -> None:
        """Schliesst den Dialog ohne Auswahl."""
        self.dismiss(None)
