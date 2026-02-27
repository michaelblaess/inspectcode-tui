$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m inspectcode_tui @args
} else {
    Write-Host "Python nicht gefunden! Bitte Python 3.10+ installieren und zum PATH hinzufuegen." -ForegroundColor Red
    Write-Host "  winget install Python.Python.3.12"
    Read-Host "Eingabetaste druecken"
}
