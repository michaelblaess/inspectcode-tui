"""Persistierte Einstellungen fuer InspectCode TUI.

Speichert und laedt Benutzereinstellungen aus
~/.inspectcode-tui/settings.json.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Persistierte Benutzereinstellungen.

    Attributes:
        theme: Name des Textual-Themes.
        log_height: Hoehe des Log-Widgets in Zeilen.
        log_visible: Ob der Log-Bereich sichtbar ist.
        no_build: Solution nicht bauen (Default).
    """

    theme: str = "textual-dark"
    log_height: int = 12
    log_visible: bool = True
    no_build: bool = True
    language: str = "de"

    SETTINGS_DIR = Path.home() / ".inspectcode-tui"
    SETTINGS_FILE = SETTINGS_DIR / "settings.json"

    def to_dict(self) -> dict:
        """Konvertiert die Einstellungen in ein Dictionary fuer JSON.

        Returns:
            Dictionary mit allen Feldern.
        """
        return {
            "theme": self.theme,
            "log_height": self.log_height,
            "log_visible": self.log_visible,
            "no_build": self.no_build,
            "language": self.language,
        }

    @staticmethod
    def load() -> Settings:
        """Laedt die Einstellungen aus der JSON-Datei.

        Gibt Default-Einstellungen zurueck bei Fehler oder fehlender Datei.

        Returns:
            Settings-Objekt.
        """
        if not Settings.SETTINGS_FILE.is_file():
            return Settings()

        try:
            raw = Settings.SETTINGS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return Settings()
            return Settings(
                theme=data.get("theme", "textual-dark"),
                log_height=data.get("log_height", 12),
                log_visible=data.get("log_visible", True),
                no_build=data.get("no_build", True),
                language=data.get("language", "de"),
            )
        except Exception as exc:
            logger.warning("Settings konnten nicht geladen werden: %s", exc)
            return Settings()

    def save(self) -> None:
        """Speichert die Einstellungen in die JSON-Datei.

        Erstellt das Verzeichnis falls es nicht existiert.
        """
        try:
            Settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            Settings.SETTINGS_FILE.write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Settings konnten nicht gespeichert werden: %s", exc)
