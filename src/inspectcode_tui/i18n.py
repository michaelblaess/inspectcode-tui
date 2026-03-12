"""Internationalisierung (i18n) fuer InspectCode TUI.

Laedt sprachspezifische Strings aus JSON-Dateien im locale-Verzeichnis.
Unterstuetzt Deutsch (de) und Englisch (en).
"""

from __future__ import annotations

import json
from importlib import resources

_strings: dict[str, str] = {}
_current_lang: str = "de"


def load_locale(lang: str) -> None:
    """Laedt die Sprachdatei fuer die angegebene Sprache.

    Args:
        lang: Sprachcode (z.B. 'de' oder 'en').
    """
    global _strings, _current_lang
    _current_lang = lang

    locale_file = resources.files("inspectcode_tui") / "locale" / f"{lang}.json"
    raw = locale_file.read_text(encoding="utf-8")
    _strings = json.loads(raw)


def t(key: str, **kwargs: object) -> str:
    """Gibt den uebersetzten String fuer den Schluessel zurueck.

    Falls der Schluessel nicht gefunden wird, wird der Schluessel selbst
    zurueckgegeben. Platzhalter in geschweiften Klammern werden durch
    die uebergebenen kwargs ersetzt.

    Args:
        key: Schluessel im Format 'gruppe.name'.
        **kwargs: Werte fuer Platzhalter im String.

    Returns:
        Uebersetzter String.
    """
    template = _strings.get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def current_lang() -> str:
    """Gibt den aktuellen Sprachcode zurueck.

    Returns:
        Sprachcode (z.B. 'de' oder 'en').
    """
    return _current_lang
