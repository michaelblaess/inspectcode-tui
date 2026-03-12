"""Summary-Widget mit Zaehler und Severity-Uebersicht."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult, RenderResult
from textual.widget import Widget
from textual.widgets import Static

from ..i18n import t
from ..models.finding import Finding


class SummaryPanel(Widget):
    """Zeigt eine Zusammenfassung der Findings."""

    DEFAULT_CSS = """
    SummaryPanel {
        height: auto;
        min-height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._findings: list[Finding] = []
        self._solution_name: str = ""

    def render(self) -> RenderResult:
        if not self._findings:
            return Text(t("summary.no_findings"), style="dim italic")

        text = Text()

        if self._solution_name:
            text.append(f" {self._solution_name}", style="bold")
            text.append("  |  ")

        total = len(self._findings)
        text.append(t("summary.findings", count=total), style="bold")
        text.append("  ")

        # Severity-Zaehler
        counts: dict[str, int] = {}
        for f in self._findings:
            sev = f.severity.upper()
            counts[sev] = counts.get(sev, 0) + 1

        severity_styles = {
            "ERROR": "bold red",
            "WARNING": "bold yellow",
            "SUGGESTION": "bold cyan",
            "HINT": "dim",
        }

        parts = []
        for sev in ["ERROR", "WARNING", "SUGGESTION", "HINT"]:
            if sev in counts:
                parts.append((f"{sev}: {counts[sev]}", severity_styles.get(sev, "")))

        for i, (label, style) in enumerate(parts):
            if i > 0:
                text.append("  |  ")
            text.append(label, style=style)

        # Kategorie-Zaehler
        categories: dict[str, int] = {}
        for f in self._findings:
            categories[f.category] = categories.get(f.category, 0) + 1

        if categories:
            text.append("\n")
            cat_parts = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            for i, (cat, count) in enumerate(cat_parts[:5]):
                if i > 0:
                    text.append("  |  ")
                text.append(f"{cat}: {count}", style="dim")
            if len(cat_parts) > 5:
                text.append(t("summary.more_categories", count=len(cat_parts) - 5), style="dim")

        return text

    def update_findings(self, findings: list[Finding], solution_name: str = "") -> None:
        """Aktualisiert die Zusammenfassung."""
        self._findings = findings
        self._solution_name = solution_name
        self.refresh()
