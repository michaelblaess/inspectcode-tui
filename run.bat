@echo off
setlocal

set PYTHONPATH=%~dp0src

where python >nul 2>nul
if %errorlevel% equ 0 (
    python -m inspectcode_tui %*
) else (
    echo Python nicht gefunden! Bitte Python 3.10+ installieren und zum PATH hinzufuegen.
    echo   winget install Python.Python.3.12
    pause
)
