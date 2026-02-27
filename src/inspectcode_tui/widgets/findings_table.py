"""DataTable-Widget fuer InspectCode Findings."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Input, Static
from textual.message import Message
from rich.text import Text

from ..models.finding import Finding


class FindingsTable(Vertical):
    """Widget mit filterbarer DataTable fuer Findings."""

    DEFAULT_CSS = """
    FindingsTable {
        height: 1fr;
    }

    FindingsTable #filter-bar {
        dock: top;
        height: 3;
        padding: 0 1;
    }

    FindingsTable #findings-count {
        dock: top;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    FindingsTable DataTable {
        height: 1fr;
    }
    """

    filter_text: reactive[str] = reactive("")

    class FindingSelected(Message):
        """Wird gesendet wenn ein Finding ausgewaehlt wird."""

        def __init__(self, finding: Finding) -> None:
            super().__init__()
            self.finding = finding

    class FindingHighlighted(Message):
        """Wird gesendet wenn der Cursor auf ein Finding bewegt wird."""

        def __init__(self, finding: Finding) -> None:
            super().__init__()
            self.finding = finding

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._findings: list[Finding] = []
        self._filtered: list[Finding] = []
        self._severity_filter: str = ""
        self._category_filter: str = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter (Datei, Nachricht, Kategorie...)", id="filter-bar")
        yield Static("", id="findings-count")
        yield DataTable(id="findings-data", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one("#findings-data", DataTable)
        table.add_columns("#", "Sev", "Datei", "Zeile", "Kategorie", "Nachricht")
        table.focus()

    def load_findings(self, findings: list[Finding]) -> None:
        """Laedt Findings in die Tabelle."""
        self._findings = findings
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Wendet den aktuellen Filter an und aktualisiert die Tabelle."""
        search = self.filter_text.lower()

        self._filtered = []
        for f in self._findings:
            if self._severity_filter and f.severity.upper() != self._severity_filter.upper():
                continue
            if self._category_filter and self._category_filter.lower() not in f.category.lower():
                continue
            if search:
                haystack = f"{f.file} {f.message} {f.category} {f.type_id}".lower()
                if search not in haystack:
                    continue
            self._filtered.append(f)

        self._refresh_table()

    def _refresh_table(self) -> None:
        """Aktualisiert die DataTable mit gefilterten Findings."""
        table = self.query_one("#findings-data", DataTable)
        table.clear()

        for idx, finding in enumerate(self._filtered, 1):
            severity_text = self._styled_severity(finding.severity)
            # Kategorie kuerzen: "CSHARP.CodeSmell" -> "CodeSmell"
            category = finding.category
            if "." in category:
                category = category.rsplit(".", 1)[-1]
            table.add_row(
                str(idx),
                severity_text,
                finding.file,
                str(finding.line),
                category,
                finding.message,
                key=str(idx - 1),
            )

        count_label = self.query_one("#findings-count", Static)
        total = len(self._findings)
        shown = len(self._filtered)
        if total == shown:
            count_label.update(f" {total} Findings")
        else:
            count_label.update(f" {shown} von {total} Findings (gefiltert)")

    def _styled_severity(self, severity: str) -> Text:
        """Erstellt farbcodierten Severity-Text."""
        sev = severity.upper()
        styles = {
            "ERROR": "bold red",
            "WARNING": "bold yellow",
            "SUGGESTION": "bold cyan",
            "HINT": "dim",
        }
        return Text(sev, style=styles.get(sev, ""))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Reagiert auf Aenderungen im Filter-Input."""
        if event.input.id == "filter-bar":
            self.filter_text = event.value
            self._apply_filter()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Reagiert auf Enter/Klick auf eine Zeile."""
        idx = int(event.row_key.value)
        if 0 <= idx < len(self._filtered):
            self.post_message(self.FindingSelected(self._filtered[idx]))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Reagiert auf Cursor-Bewegung."""
        if event.row_key is None:
            return
        idx = int(event.row_key.value)
        if 0 <= idx < len(self._filtered):
            self.post_message(self.FindingHighlighted(self._filtered[idx]))

    def set_severity_filter(self, severity: str) -> None:
        """Setzt den Severity-Filter."""
        self._severity_filter = severity
        self._apply_filter()

    def set_category_filter(self, category: str) -> None:
        """Setzt den Kategorie-Filter."""
        self._category_filter = category
        self._apply_filter()

    def get_selected_finding(self) -> Finding | None:
        """Gibt das aktuell ausgewaehlte Finding zurueck."""
        table = self.query_one("#findings-data", DataTable)
        if table.row_count == 0:
            return None
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        idx = int(row_key.value)
        if 0 <= idx < len(self._filtered):
            return self._filtered[idx]
        return None
