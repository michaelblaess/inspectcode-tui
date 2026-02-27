"""History-Modell fuer InspectCode TUI.

Speichert und laedt vergangene Scan-Konfigurationen aus
~/.inspectcode-tui/history.json.
"""

from __future__ import annotations

import getpass
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Einzelner Eintrag in der Scan-History.

    Speichert alle Parameter eines Scans, damit dieser
    spaeter wiederholt werden kann.

    Attributes:
        solution_path: Pfad zur .sln- oder .csproj-Datei.
        project: Optionaler Projektname.
        severity: Minimale Severity.
        no_build: Solution nicht bauen.
        commit: Git-Commit-Referenz (leer = kein Git-Modus).
        timestamp: Zeitstempel im ISO-Format.
        user: Benutzername zum Zeitpunkt des Scans.
    """

    solution_path: str
    project: str = ""
    severity: str = "WARNING"
    no_build: bool = True
    commit: str = ""
    timestamp: str = ""
    user: str = ""

    def to_dict(self) -> dict:
        """Konvertiert den Eintrag in ein Dictionary fuer JSON.

        Returns:
            Dictionary mit allen Feldern.
        """
        return {
            "solution_path": self.solution_path,
            "project": self.project,
            "severity": self.severity,
            "no_build": self.no_build,
            "commit": self.commit,
            "timestamp": self.timestamp,
            "user": self.user,
        }

    @staticmethod
    def from_dict(data: dict) -> HistoryEntry:
        """Erstellt einen HistoryEntry aus einem Dictionary.

        Args:
            data: Dictionary mit den Feldern des Eintrags.

        Returns:
            Neuer HistoryEntry.
        """
        return HistoryEntry(
            solution_path=data.get("solution_path", ""),
            project=data.get("project", ""),
            severity=data.get("severity", "WARNING"),
            no_build=data.get("no_build", True),
            commit=data.get("commit", ""),
            timestamp=data.get("timestamp", ""),
            user=data.get("user", ""),
        )

    def display_label(self) -> str:
        """Erzeugt ein kompaktes Label fuer die Anzeige in der History-Liste.

        Format: "2026-02-13 14:30 | Solution.sln | --severity WARNING"

        Returns:
            Kurzform-String fuer die Listenanzeige.
        """
        date_part = self.timestamp[:16].replace("T", " ") if self.timestamp else "?"

        # Solution-Name extrahieren (nur Dateiname)
        sol_name = Path(self.solution_path).name if self.solution_path else "?"

        parts = [date_part, sol_name]

        if self.project:
            parts.append(f"--project {self.project}")

        if self.severity != "WARNING":
            parts.append(f"--severity {self.severity}")

        if not self.no_build:
            parts.append("--build")

        if self.commit:
            parts.append(f"--commit {self.commit}")

        return " | ".join(parts)


class History:
    """Verwaltet die Scan-History in ~/.inspectcode-tui/history.json.

    Stellt statische Methoden zum Laden, Speichern und Hinzufuegen
    von History-Eintraegen bereit.
    """

    HISTORY_DIR = Path.home() / ".inspectcode-tui"
    HISTORY_FILE = HISTORY_DIR / "history.json"
    MAX_ENTRIES = 50

    @staticmethod
    def load() -> list[HistoryEntry]:
        """Laedt die History aus der JSON-Datei.

        Gibt eine leere Liste zurueck bei Fehler oder fehlender Datei.

        Returns:
            Liste der HistoryEntry-Objekte (neueste zuerst).
        """
        if not History.HISTORY_FILE.is_file():
            return []

        try:
            raw = History.HISTORY_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                return []
            return [HistoryEntry.from_dict(item) for item in data]
        except Exception as exc:
            logger.warning("History konnte nicht geladen werden: %s", exc)
            return []

    @staticmethod
    def save(entries: list[HistoryEntry]) -> None:
        """Speichert die History in die JSON-Datei.

        Erstellt das Verzeichnis falls es nicht existiert.

        Args:
            entries: Liste der HistoryEntry-Objekte.
        """
        try:
            History.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            data = [entry.to_dict() for entry in entries]
            History.HISTORY_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("History konnte nicht gespeichert werden: %s", exc)

    @staticmethod
    def add(entry: HistoryEntry) -> None:
        """Fuegt einen neuen Eintrag an den Anfang der History hinzu.

        Laedt die aktuelle History, stellt den neuen Eintrag voran,
        kuerzt auf MAX_ENTRIES und speichert.

        Args:
            entry: Der neue HistoryEntry.
        """
        # Timestamp und User setzen falls nicht vorhanden
        if not entry.timestamp:
            entry.timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not entry.user:
            try:
                entry.user = getpass.getuser()
            except Exception:
                entry.user = "unknown"

        entries = History.load()
        entries.insert(0, entry)

        # Auf Maximum kuerzen
        if len(entries) > History.MAX_ENTRIES:
            entries = entries[:History.MAX_ENTRIES]

        History.save(entries)
