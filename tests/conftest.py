"""Gemeinsame Test-Vorbereitung.

**Kein Test darf in das echte Benutzerverzeichnis schreiben.** Die App legt
Einstellungen und Verlauf unter ``~/.inspectcode-tui`` ab. Die Pfade stehen als
Klassenkonstanten fest und werden beim Import einmal aus ``Path.home()``
berechnet - das Umbiegen von ``HOME`` allein genuegt deshalb nicht, sie werden
einzeln umgehaengt.

Ausserdem wechselt jeder Test in ein leeres Arbeitsverzeichnis, weil die App
dort nach einer ``whitelist.json`` sucht.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inspectcode_tui.i18n import load_locale
from inspectcode_tui.models.history import History
from inspectcode_tui.models.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt Einstellungen, Verlauf und Arbeitsverzeichnis in Wegwerf-Ordner."""
    home = tmp_path_factory.mktemp("home")
    data_dir = home / ".inspectcode-tui"

    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Settings, "SETTINGS_DIR", data_dir)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", data_dir / "settings.json")
    monkeypatch.setattr(History, "HISTORY_DIR", data_dir)
    monkeypatch.setattr(History, "HISTORY_FILE", data_dir / "history.json")
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))

    # Ohne geladene Sprache liefert t() nur die Schluessel zurueck
    load_locale("de")
    return home


@pytest.fixture
def fixtures_dir() -> Path:
    """Ordner mit den Beispiel-Reports."""
    return FIXTURES
