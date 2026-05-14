"""ModalScreen fuer die Bestaetigung eines Fixes."""

from __future__ import annotations

from dataclasses import dataclass

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static

from ..i18n import t
from ..models.finding import Finding
from ..services.fixer import FixResult


@dataclass
class FixDecision:
    """Ergebnis der Benutzer-Entscheidung im Fix-Dialog."""

    confirmed: bool


class ConfirmFixScreen(ModalScreen[FixDecision]):
    """Modal-Dialog zur Bestaetigung eines Fixes."""

    DEFAULT_CSS = """
    ConfirmFixScreen {
        align: center middle;
    }

    #fix-dialog {
        width: 90;
        height: auto;
        max-height: 40;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #fix-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #fix-info {
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
    }

    #fix-preview {
        width: 100%;
        height: auto;
        max-height: 20;
        overflow-y: auto;
        border: round $accent;
        padding: 0 1;
    }

    #fix-buttons {
        width: 100%;
        height: 3;
        align: center middle;
        padding-top: 1;
    }

    #fix-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "placeholder"),
    ]

    def __init__(self, finding: Finding, preview: FixResult) -> None:
        super().__init__()
        self.finding = finding
        self.preview = preview

    def compose(self) -> ComposeResult:
        with Vertical(id="fix-dialog"):
            yield Static(t("confirm_fix.title"), id="fix-title")
            yield Static(self._build_info(), id="fix-info")
            yield RichLog(id="fix-preview", highlight=True)
            from textual.containers import Horizontal

            with Horizontal(id="fix-buttons"):
                yield Button(t("confirm_fix.button_fix"), variant="success", id="btn-fix")
                yield Button(t("confirm_fix.button_cancel"), variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        """Zeigt die Vorschau beim Laden."""
        preview_log = self.query_one("#fix-preview", RichLog)

        if self.preview.old_content and self.preview.new_content:
            import difflib

            old_lines = self.preview.old_content.splitlines()
            new_lines = self.preview.new_content.splitlines()

            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=t("confirm_fix.before"),
                tofile=t("confirm_fix.after"),
                lineterm="",
                n=3,
            )
            diff_text = "\n".join(diff)
            if diff_text:
                syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
                preview_log.write(syntax)
            else:
                preview_log.write(t("confirm_fix.no_changes"))
        else:
            preview_log.write(t("confirm_fix.no_preview"))

    def _build_info(self) -> str:
        """Erstellt den Info-Text fuer den Dialog."""
        f = self.finding
        return (
            f"[bold]{f.type_id}[/bold]\n"
            f"{t('confirm_fix.file', file=f.file, line=f.line)}\n"
            f"{t('confirm_fix.message', message=f.message)}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-fix":
            self.dismiss(FixDecision(confirmed=True))
        else:
            self.dismiss(FixDecision(confirmed=False))

    def action_cancel(self) -> None:
        self.dismiss(FixDecision(confirmed=False))
