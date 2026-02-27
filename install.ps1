# ============================================================
#  InspectCode TUI - Installer (PowerShell)
#
#  Verwendung:
#    irm https://raw.githubusercontent.com/michaelblaess/inspectcode-tui/main/install.ps1 | iex
#
#  Laedt das neueste Release von GitHub herunter und installiert es.
#  Keine Abhaengigkeiten noetig (kein Python, kein Git).
#  JetBrains CLI Tools (jb inspectcode) muessen separat installiert sein.
#
#  Installiert nach: %LOCALAPPDATA%\inspectcode-tui\
#  Erstellt Wrapper:  %LOCALAPPDATA%\inspectcode-tui\bin\inspectcode-tui.cmd
# ============================================================

$ErrorActionPreference = "Stop"

$Repo = "michaelblaess/inspectcode-tui"
$InstallDir = Join-Path $env:LOCALAPPDATA "inspectcode-tui"
$BinDir = Join-Path $InstallDir "bin"
$Wrapper = Join-Path $BinDir "inspectcode-tui.cmd"

Write-Host ""
Write-Host "  +================================================+" -ForegroundColor Cyan
Write-Host "  |   InspectCode TUI - Installer                  |" -ForegroundColor Cyan
Write-Host "  +================================================+" -ForegroundColor Cyan
Write-Host ""

# --- Architektur erkennen ---
$Arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
$Artifact = "inspectcode-tui-win-${Arch}"
$Archive = "${Artifact}.zip"

Write-Host "  Plattform: Windows ($Arch)"
Write-Host ""

# --- Neuestes Release von GitHub ermitteln ---
Write-Host "  Suche neuestes Release..."
$ApiUrl = "https://api.github.com/repos/${Repo}/releases/latest"

try {
    $Release = Invoke-RestMethod -Uri $ApiUrl -UseBasicParsing
} catch {
    Write-Host "  [FEHLER] Konnte GitHub API nicht erreichen." -ForegroundColor Red
    Write-Host "  Pruefe deine Internetverbindung."
    exit 1
}

# Download-URL finden
$Asset = $Release.assets | Where-Object { $_.name -eq $Archive } | Select-Object -First 1

if (-not $Asset) {
    Write-Host "  [FEHLER] Kein Release fuer ${Archive} gefunden!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Verfuegbare Assets:"
    $Release.assets | ForEach-Object { Write-Host "    $($_.name)" }
    Write-Host ""
    Write-Host "  Moeglicherweise gibt es noch kein Release fuer deine Plattform."
    exit 1
}

$DownloadUrl = $Asset.browser_download_url
$Version = $Release.tag_name
Write-Host "  [OK] Release gefunden: $Version" -ForegroundColor Green
Write-Host ""

# --- Download ---
$TmpDir = Join-Path $env:TEMP "inspectcode-tui-install"
if (Test-Path $TmpDir) { Remove-Item -Recurse -Force $TmpDir }
New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
$TmpFile = Join-Path $TmpDir $Archive

Write-Host "  Lade herunter: $Archive"
try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $TmpFile -UseBasicParsing
} catch {
    # Fallback fuer aeltere PowerShell
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    (New-Object System.Net.WebClient).DownloadFile($DownloadUrl, $TmpFile)
}
Write-Host "  [OK] Download abgeschlossen" -ForegroundColor Green
Write-Host ""

# --- Entpacken ---
Write-Host "  Entpacke nach: $InstallDir"

# Alte Installation sichern
if (Test-Path $InstallDir) {
    $BackupDir = "${InstallDir}.bak"
    if (Test-Path $BackupDir) { Remove-Item -Recurse -Force $BackupDir }
    Rename-Item -Path $InstallDir -NewName "$($InstallDir).bak"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Expand-Archive -Path $TmpFile -DestinationPath $InstallDir -Force
Remove-Item -Recurse -Force $TmpDir

# Alte Sicherung entfernen
$BackupDir = "${InstallDir}.bak"
if (Test-Path $BackupDir) { Remove-Item -Recurse -Force $BackupDir }

Write-Host "  [OK] Entpackt" -ForegroundColor Green
Write-Host ""

# --- Wrapper erstellen ---
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

$ExePath = Join-Path $InstallDir "inspectcode-tui.exe"

$WrapperContent = @"
@echo off
REM InspectCode TUI - Wrapper (automatisch generiert)
"$ExePath" %*
"@
Set-Content -Path $Wrapper -Value $WrapperContent -Encoding ASCII
Write-Host "  [OK] Wrapper erstellt" -ForegroundColor Green

# --- PATH pruefen und ergaenzen ---
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    Write-Host ""
    Write-Host "  Fuege zum PATH hinzu: $BinDir" -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$BinDir;$UserPath", "User")
    $env:Path = "$BinDir;$env:Path"
    Write-Host "  [OK] PATH aktualisiert" -ForegroundColor Green
}

# --- Fertig ---
Write-Host ""
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host "  |   Installation abgeschlossen! ($Version)" -ForegroundColor Green
Write-Host "  +================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Starten mit:"
Write-Host "    inspectcode-tui MeineSolution.sln" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Voraussetzung:"
Write-Host "    JetBrains CLI Tools muessen installiert sein:" -ForegroundColor Gray
Write-Host "    dotnet tool install -g JetBrains.ReSharper.GlobalTools" -ForegroundColor Gray
Write-Host ""
Write-Host "  Aktualisieren:"
Write-Host "    Installer erneut ausfuehren." -ForegroundColor Gray
Write-Host ""
Write-Host "  Deinstallieren:" -ForegroundColor Gray
Write-Host "    Remove-Item -Recurse '$InstallDir'" -ForegroundColor Gray
Write-Host ""
Write-Host "  HINWEIS: Oeffne ein neues Terminal, damit der PATH wirkt." -ForegroundColor Yellow
Write-Host ""
