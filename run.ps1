#Requires -Version 5.1
# run.ps1 - starts inspectcode-tui from source.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Please run .\bootstrap.ps1 first." -ForegroundColor Red
    exit 1
}

& ".venv\Scripts\python.exe" -m inspectcode_tui @args
