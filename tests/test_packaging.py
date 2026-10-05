"""Paketinhalt: Stylesheet und Sprachdateien muessen ins Wheel.

In einer frueheren Fassung fehlte ``app.tcss`` im Wheel. Textual sucht
``CSS_PATH`` relativ zum Modul der App - fehlt die Datei dort, bricht der
Start nach ``pip install`` ab, waehrend er aus dem Quellbaum funktioniert.
"""

from __future__ import annotations

import tomllib
from fnmatch import fnmatch
from importlib import resources
from pathlib import Path

import inspectcode_tui
from inspectcode_tui import app as app_module
from inspectcode_tui.app import InspectCodeApp

PACKAGE_DIR = Path(inspectcode_tui.__file__).parent
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_css_path_liegt_neben_dem_app_modul() -> None:
    css = Path(app_module.__file__).parent / InspectCodeApp.CSS_PATH

    assert css.is_file(), f"{css} fehlt"
    assert css.read_text(encoding="utf-8").strip(), "app.tcss ist leer"


def test_css_ueber_importlib_resources_erreichbar() -> None:
    assert (resources.files("inspectcode_tui") / InspectCodeApp.CSS_PATH).is_file()


def test_package_data_deckt_alle_nicht_python_dateien_ab() -> None:
    # Jede Datei, die die App zur Laufzeit liest, muss von package-data erfasst sein
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["inspectcode_tui"]

    benoetigt = [
        path.relative_to(PACKAGE_DIR).as_posix()
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file() and path.suffix in {".tcss", ".json"}
    ]

    assert InspectCodeApp.CSS_PATH in benoetigt
    assert "locale/de.json" in benoetigt and "locale/en.json" in benoetigt
    fehlend = [name for name in benoetigt if not any(fnmatch(name, pattern) for pattern in patterns)]
    assert fehlend == [], f"Nicht in package-data: {fehlend}"


def test_main_nutzt_nur_absolute_imports() -> None:
    """Nuitka kompiliert __main__.py ohne Parent-Package, relative Imports scheitern dort."""
    quelle = (Path(__file__).parent.parent / "src" / "inspectcode_tui" / "__main__.py").read_text(encoding="utf-8")
    relativ = [zeile.strip() for zeile in quelle.splitlines() if zeile.strip().startswith("from .")]
    assert relativ == []
