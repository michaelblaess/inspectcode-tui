"""Modal-Screen fuer Top-10-Findings Chart."""

from __future__ import annotations

from collections import Counter

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static
from rich.text import Text

from ..i18n import t
from ..models.finding import Finding


# Maximale Laenge fuer Labels in der Anzeige
MAX_LABEL_LEN = 80
# Breite des Balkens
BAR_WIDTH = 40


class TopFindingsScreen(ModalScreen):
    """Modal-Dialog mit Top-10-Findings als Balkendiagramm."""

    DEFAULT_CSS = """
    TopFindingsScreen {
        align: center middle;
    }

    TopFindingsScreen > VerticalScroll {
        width: 90%;
        max-width: 120;
        height: 85%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    TopFindingsScreen #top-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    TopFindingsScreen #top-footer {
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

    def __init__(self, findings: list[Finding], **kwargs) -> None:
        super().__init__(**kwargs)
        self._findings = findings
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
        with VerticalScroll():
            yield Static(t("top.title"), id="top-title")
            yield Static(self._build_chart(), id="top-content")
            yield Static(t("top.footer"), id="top-footer")

    def _build_chart(self) -> Text:
        """Erstellt das Balkendiagramm der Top-10-Findings.

        Returns:
            Formatierter Rich Text mit Balkendiagramm.
        """
        text = Text()

        if not self._findings:
            text.append(t("top.no_findings"), style="green bold")
            return text

        total = len(self._findings)
        text.append(t("top.total", count=total) + "\n", style="bold")
        text.append("\n")

        # === Top 10 Finding-Typen ===
        type_counter: Counter = Counter()
        for finding in self._findings:
            type_counter[finding.type_id] += 1

        if type_counter:
            _append_section(text, t("top.types"), type_counter, "red")

        # === Top 10 Kategorien ===
        category_counter: Counter = Counter()
        for finding in self._findings:
            category_counter[finding.category or t("top.no_category")] += 1

        if category_counter:
            _append_section(text, t("top.categories"), category_counter, "yellow")

        # === Top 10 Dateien ===
        file_counter: Counter = Counter()
        for finding in self._findings:
            file_counter[finding.file] += 1

        if file_counter:
            _append_section(text, t("top.files"), file_counter, "cyan")

        return text

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()


def _append_section(text: Text, title: str, counter: Counter, color: str) -> None:
    """Fuegt eine Chart-Sektion mit Balkendiagramm hinzu.

    Args:
        text: Rich Text zum Anhaengen.
        title: Titel der Sektion.
        counter: Counter mit Label -> Anzahl.
        color: Farbe der Balken.
    """
    text.append(f"{title}\n", style=f"bold {color} underline")
    text.append("\n")

    max_count = counter.most_common(1)[0][1] if counter else 1
    for rank, (label, count) in enumerate(counter.most_common(10), 1):
        display = _truncate(label, MAX_LABEL_LEN)
        _append_bar_entry(text, rank, display, count, max_count, color)

    text.append("\n")


def _truncate(label: str, max_len: int) -> str:
    """Kuerzt einen Text auf maximale Laenge.

    Args:
        label: Der zu kuerzende Text.
        max_len: Maximale Laenge.

    Returns:
        Gekuerzter Text.
    """
    if len(label) <= max_len:
        return label
    return f"{label[:max_len - 3]}..."


def _append_bar_entry(
    text: Text,
    rank: int,
    label: str,
    count: int,
    max_count: int,
    color: str,
) -> None:
    """Fuegt einen Chart-Eintrag hinzu (Label ueber Balken).

    Layout:
      1. Finding-Typ hier...
         ████████████████████████████ 15x

    Args:
        text: Rich Text zum Anhaengen.
        rank: Rang-Nummer.
        label: Beschreibungstext.
        count: Anzahl.
        max_count: Maximaler Wert (fuer Balkenbreite).
        color: Farbe des Balkens.
    """
    # Zeile 1: Rang + Label
    text.append(f"  {rank:2d}. ", style="bold")
    text.append(f"{label}\n", style="")

    # Zeile 2: Eingerueckter Balken + Anzahl
    bar_len = max(1, int(BAR_WIDTH * count / max_count)) if max_count > 0 else 1
    bar = "\u2588" * bar_len
    padding = " " * 6  # Einrueckung passend zum Label
    text.append(f"{padding}{bar}", style=f"bold {color}")
    text.append(f" {count}x\n", style="bold")
