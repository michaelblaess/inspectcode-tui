#!/usr/bin/env bash
# ============================================================
#  InspectCode TUI - Setup
#  Richtet eine virtuelle Umgebung ein und installiert alles.
#  Voraussetzung: Python 3.10+ muss installiert sein.
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   InspectCode TUI - Setup                    ║"
echo "  ╚══════════════════════════════════════════════╝"
echo

# --- Python pruefen ---
if ! command -v python3 &> /dev/null; then
    echo "  [FEHLER] Python wurde nicht gefunden!"
    echo "  Bitte Python 3.10+ installieren."
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo "  [OK] $PYVER gefunden"
echo

# --- Virtuelle Umgebung erstellen ---
if [ -x "$VENV_DIR/bin/python" ]; then
    echo "  [OK] Virtuelle Umgebung existiert bereits"
else
    echo "  Erstelle virtuelle Umgebung..."
    python3 -m venv "$VENV_DIR"
    echo "  [OK] Virtuelle Umgebung erstellt"
fi
echo

# --- pip upgrade ---
echo "  Aktualisiere pip..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip --quiet
echo "  [OK] pip aktualisiert"
echo

# --- Paket installieren ---
echo "  Installiere InspectCode TUI + Abhaengigkeiten..."
"$VENV_DIR/bin/pip" install --upgrade -e "$SCRIPT_DIR" --quiet
echo "  [OK] InspectCode TUI installiert"
echo

# --- Fertig ---
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   Setup abgeschlossen!                       ║"
echo "  ╠══════════════════════════════════════════════╣"
echo "  ║                                              ║"
echo "  ║   Starten mit:                               ║"
echo "  ║     ./run.sh pfad/zu/ergebnis.xml            ║"
echo "  ║                                              ║"
echo "  ╚══════════════════════════════════════════════╝"
echo
