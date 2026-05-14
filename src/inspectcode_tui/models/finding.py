"""Dataclass fuer ein einzelnes InspectCode Finding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Finding:
    """Repraesentiert ein einzelnes InspectCode Finding."""

    type_id: str
    file: str
    line: int
    offset: str
    message: str
    severity: str
    category: str
    category_id: str
    description: str
    project_name: str
    wiki_url: str = ""

    @property
    def filename(self) -> str:
        """Gibt nur den Dateinamen ohne Pfad zurueck."""
        return self.file.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

    @property
    def severity_icon(self) -> str:
        """Gibt ein Icon fuer die Severity zurueck."""
        icons = {
            "ERROR": "\u2718",  # ✘
            "WARNING": "\u26a0",  # ⚠
            "SUGGESTION": "\u2139",  # ℹ
            "HINT": "\u2022",  # •
        }
        return icons.get(self.severity.upper(), "?")
