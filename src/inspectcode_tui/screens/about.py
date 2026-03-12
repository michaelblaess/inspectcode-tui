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
from ..i18n import t


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

        text.append(t("about.description") + "\n")
        text.append(t("about.engine") + "\n\n")

        text.append("\u2500" * 44 + "\n\n", style="dim")

        text.append(t("about.quote") + "\n\n", style="italic")
        text.append(t("about.quote_author"), style="bold")

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
        Binding("escape", "close", "placeholder"),
        Binding("q", "close", "placeholder"),
        Binding("i", "close", "placeholder", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
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
            yield Static(t("about.title"), id="about-title")
            yield AboutContent()
            yield Static(t("about.footer"), id="about-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
