"""ModalScreen fuer die Diff-Ansicht."""

from __future__ import annotations

import difflib

from rich.syntax import Syntax
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static


class DiffViewScreen(ModalScreen[bool]):
    """Modal-Dialog der einen Diff anzeigt."""

    DEFAULT_CSS = """
    DiffViewScreen {
        align: center middle;
    }

    #diff-dialog {
        width: 95%;
        height: 90%;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #diff-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #diff-content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
        border: round $accent;
        padding: 0 1;
    }

    #diff-close-bar {
        width: 100%;
        height: 3;
        align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "close", "Schliessen"),
        ("q", "close", "Schliessen"),
    ]

    def __init__(
        self,
        old_content: str,
        new_content: str,
        title: str = "Diff-Ansicht",
        old_label: str = "vorher",
        new_label: str = "nachher",
    ) -> None:
        super().__init__()
        self.old_content = old_content
        self.new_content = new_content
        self.diff_title = title
        self.old_label = old_label
        self.new_label = new_label

    def compose(self) -> ComposeResult:
        with Vertical(id="diff-dialog"):
            yield Static(self.diff_title, id="diff-title")
            yield RichLog(id="diff-content", highlight=True)
            from textual.containers import Horizontal
            with Horizontal(id="diff-close-bar"):
                yield Button("Schliessen", variant="primary", id="btn-close")

    def on_mount(self) -> None:
        """Zeigt den Diff beim Laden."""
        log = self.query_one("#diff-content", RichLog)

        old_lines = self.old_content.splitlines()
        new_lines = self.new_content.splitlines()

        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=self.old_label,
            tofile=self.new_label,
            lineterm="",
            n=5,
        )

        diff_text = "\n".join(diff)
        if diff_text:
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
            log.write(syntax)
        else:
            log.write(Text("Keine Unterschiede.", style="dim italic"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(True)

    def action_close(self) -> None:
        self.dismiss(True)
