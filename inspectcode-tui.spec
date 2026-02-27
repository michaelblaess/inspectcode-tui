# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Spec fuer InspectCode TUI.

Baut eine Standalone-EXE (--onedir) mit allen Abhaengigkeiten.
Kein Playwright/Chromium noetig - nur Textual + Rich.

Ausfuehren: pyinstaller inspectcode-tui.spec
"""

import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

src_pkg = os.path.join("src", "inspectcode_tui")

a = Analysis(
    [os.path.join(src_pkg, "__main__.py")],
    pathex=["src"],
    binaries=[],
    datas=[
        # App-eigene Dateien
        (os.path.join(src_pkg, "app.tcss"), "inspectcode_tui"),
    ],
    hiddenimports=[
        "inspectcode_tui",
        "inspectcode_tui.__main__",
        "inspectcode_tui.app",
        "inspectcode_tui.models",
        "inspectcode_tui.models.finding",
        "inspectcode_tui.models.report",
        "inspectcode_tui.models.settings",
        "inspectcode_tui.models.history",
        "inspectcode_tui.widgets",
        "inspectcode_tui.widgets.findings_table",
        "inspectcode_tui.widgets.code_view",
        "inspectcode_tui.widgets.summary_panel",
        "inspectcode_tui.screens",
        "inspectcode_tui.screens.about",
        "inspectcode_tui.screens.confirm_fix",
        "inspectcode_tui.screens.diff_view",
        "inspectcode_tui.screens.history",
        "inspectcode_tui.screens.top_findings",
        "inspectcode_tui.services",
        "inspectcode_tui.services.inspector",
        "inspectcode_tui.services.fixer",
        # Textual braucht diverse versteckte Imports
        "textual",
        "textual.app",
        "textual.widgets",
        "textual.widgets._data_table",
        "textual.widgets._header",
        "textual.widgets._footer",
        "textual.widgets._input",
        "textual.widgets._static",
        "textual.widgets._rich_log",
        "textual.containers",
        "textual.screen",
        "textual.binding",
        "textual.css",
        "textual.css.query",
        "textual._xterm_parser",
        "textual._win_sleep",
        # Rich
        "rich",
        "rich.text",
        "rich.markup",
        "rich.highlighter",
        "rich.syntax",
    ] + collect_submodules("rich._unicode_data") + [
        # Textual-Themes
        "textual_themes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc",
        "doctest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="inspectcode-tui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="inspectcode-tui",
)
