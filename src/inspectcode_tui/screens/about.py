"""About-Screen fuer InspectCode TUI."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult, RenderResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static

from .. import __author__, __version__, __year__


class AboutContent(Widget):
    """Rendert den About-Inhalt als Rich Text."""

    DEFAULT_CSS = """
    AboutContent {
        height: auto;
        padding: 1 2;
    }
    """

    def render(self) -> RenderResult:
        """Erstellt den About-Text."""
        text = Text()
        text.append(f"v{__version__}", style="bold")
        text.append("  \u00b7  ", style="dim")
        text.append(__author__, style="bold")
        text.append("  \u00b7  ", style="dim")
        text.append(__year__, style="bold")
        text.append("\n\n")

        text.append("Terminal UI fuer JetBrains InspectCode Ergebnisse\n")
        text.append("Analyse-Engine: ReSharper CLI (jb inspectcode)\n\n")

        text.append("\u2500" * 44 + "\n\n", style="dim")

        text.append(
            "\u201eJeder Idiot kann Code schreiben,\n"
            "den ein Computer versteht.\n"
            "Gute Programmierer schreiben Code,\n"
            "den Menschen verstehen.\u201c\n\n",
            style="italic",
        )
        text.append("  \u2014 Martin Fowler", style="bold")

        return text


class AboutScreen(ModalScreen):
    """Modal-Dialog mit Informationen ueber die Anwendung."""

    DEFAULT_CSS = """
    AboutScreen {
        align: center middle;
    }

    AboutScreen > VerticalScroll {
        width: 60;
        height: 30;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    AboutScreen #about-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    AboutScreen #about-footer {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Schliessen"),
        Binding("q", "close", "Schliessen"),
        Binding("i", "close", "Schliessen", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        with VerticalScroll():
            yield Static("InspectCode TUI", id="about-title")
            yield AboutContent()
            yield Static("ESC = Schliessen", id="about-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
