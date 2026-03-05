@echo off
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m inspectcode_tui %*
) else (
    python -m inspectcode_tui %*
)
