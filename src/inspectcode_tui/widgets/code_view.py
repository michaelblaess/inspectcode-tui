"""Widget fuer Syntax-Highlighted Code-Anzeige."""

from __future__ import annotations

from pathlib import Path

from rich.style import Style
from rich.syntax import Syntax
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from ..i18n import t

# Mapping von Dateiendungen zu Rich-Sprachen
LANGUAGE_MAP = {
    ".cs": "csharp",
    ".cshtml": "html",
    ".js": "javascript",
    ".ts": "typescript",
    ".css": "css",
    ".xml": "xml",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".py": "python",
    ".sql": "sql",
    ".config": "xml",
    ".csproj": "xml",
    ".sln": "text",
}

# Auffaelliger Hintergrund fuer die Problem-Zeile
HIGHLIGHT_STYLE = Style(bgcolor="dark_red")


class CodeView(VerticalScroll, can_focus=True):
    """Scrollbares Widget das Quellcode mit Syntax-Highlighting anzeigt."""

    DEFAULT_CSS = """
    CodeView {
        height: 1fr;
        border: round $accent;
    }

    CodeView #code-content {
        height: auto;
        width: auto;
    }
    """

    file_path_label: reactive[str] = reactive("")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._code: str = ""
        self._language: str = "csharp"
        self._highlight_line: int = 0

    def compose(self) -> ComposeResult:
        """Erstellt den inneren Static-Container."""
        yield Static(
            Text(t("code.no_code"), style="dim italic"),
            id="code-content",
        )

    def load_file(self, file_path: str | Path, highlight_line: int = 0) -> bool:
        """Laedt eine Datei und zeigt sie mit Highlighting an.

        Args:
            file_path: Pfad zur Datei.
            highlight_line: Zeilennummer die hervorgehoben werden soll.

        Returns:
            True wenn die Datei geladen wurde, False bei Fehler.
        """
        path = Path(file_path)
        if not path.exists():
            self._code = ""
            self.file_path_label = t("code.file_not_found", path=path)
            self._update_content()
            return False

        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            try:
                content = path.read_text(encoding="latin-1")
            except OSError:
                self._code = ""
                self.file_path_label = t("code.read_error", path=path)
                self._update_content()
                return False

        suffix = path.suffix.lower()
        self._language = LANGUAGE_MAP.get(suffix, "text")
        self._highlight_line = highlight_line
        self._code = content
        self.file_path_label = str(path)

        self._update_content()

        # Zur Problem-Zeile scrollen (nach Render)
        if highlight_line > 0:
            self.call_after_refresh(self._scroll_to_line, highlight_line)

        return True

    def _update_content(self) -> None:
        """Aktualisiert den Static-Widget-Inhalt mit Syntax-Highlighting."""
        content_widget = self.query_one("#code-content", Static)

        if not self._code:
            content_widget.update(Text(t("code.no_code"), style="dim italic"))
            return

        syntax = Syntax(
            self._code,
            self._language,
            theme="monokai",
            line_numbers=True,
            indent_guides=True,
            word_wrap=False,
            highlight_lines={self._highlight_line} if self._highlight_line > 0 else None,
        )

        # Zusaetzlich die gesamte Problem-Zeile mit Hintergrund markieren
        if self._highlight_line > 0:
            lines = self._code.splitlines()
            if 0 < self._highlight_line <= len(lines):
                line_len = len(lines[self._highlight_line - 1])
                syntax.stylize_range(
                    HIGHLIGHT_STYLE,
                    (self._highlight_line, 0),
                    (self._highlight_line, max(line_len, 200)),
                )

        content_widget.update(syntax)

    def _scroll_to_line(self, line: int) -> None:
        """Scrollt zur angegebenen Zeile (mit Kontext darueber).

        Args:
            line: Zielzeile (1-basiert).
        """
        target_y = max(0, line - 10)
        self.scroll_to(0, target_y, animate=False)
