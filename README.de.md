# InspectCode TUI

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <a href="README.md">English</a> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <b>Deutsch</b>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/inspectcode-tui?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/inspectcode-tui/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/inspectcode-tui?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/inspectcode-tui/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/inspectcode-tui?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/inspectcode-tui/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/inspectcode-tui?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/inspectcode-tui/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/inspectcode-tui?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/inspectcode-tui/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

Terminal-UI zum Durchsuchen und Beheben von C# und .NET-Problemen mit [InspectCode](https://www.jetbrains.com/help/resharper/InspectCode.html) von JetBrains.

Gebaut mit [Textual](https://textual.textualize.io/) und [Rich](https://rich.readthedocs.io/).

![inspectcode-tui Hauptansicht](docs/screenshots/01-main.png)
*Findings-Tabelle, Quellcode mit Syntax-Highlighting, Log*

| | |
|---|---|
| ![Top 10 Chart](docs/screenshots/02-top-10.png) | ![Fix-Dialog](docs/screenshots/03-fix-code.png) |
| *Top 10 — Finding-Typen, Kategorien, Dateien* | *Auto-Fix mit Diff-Vorschau* |

| | |
|---|---|
| ![Gemstone Theme](docs/screenshots/04-atari-st-theme.png) | ![Classic Terminal Theme](docs/screenshots/05-ibm-theme.png) |
| *Gemstone — Monochromer GEM Desktop* | *Classic Terminal — Phosphor-Gruen* |

---

## Warum InspectCode?

Linter wie ESLint, StyleCop oder `dotnet format` prüfen **Stil und Syntax** - Namenskonventionen, fehlende Klammern, unbenutzte Imports. Das ist nützlich, aber es kratzt nur an der Oberfläche.

JetBrains InspectCode (die Engine hinter ReSharper) macht **tiefgehende statische Analyse** deines .NET-Codes. Es versteht dein Typsystem, den Kontrollfluss und den Datenfluss und findet Bugs, die kein Linter erkennt:

- **Null-Referenz-Pfade** - "diese Variable *kann* hier null sein, und du prüfst nicht"
- **Toter Code** - "diese Bedingung ist immer false, dieser Zweig wird nie ausgeführt"
- **Mögliche InvalidOperationException** - "dieser `.Value`-Zugriff auf ein Nullable wirft zur Laufzeit"
- **Mehrfache Enumeration** - "du iterierst dieses `IEnumerable` zweimal, was unerwartetes Verhalten oder Performance-Probleme verursachen kann"
- **Virtuelle Aufrufe in Konstruktoren** - "dieser überschreibbare Methodenaufruf im Konstruktor verhält sich in abgeleiteten Klassen anders"

Das sind **Laufzeit-Bugs auf Abruf**, die jeden Linter, jede Compiler-Warnung und jedes Code-Review passieren. InspectCode findet sie, bevor es deine User tun.

Das Problem: InspectCode produziert einen rohen Report (XML oder SARIF/JSON) mit Hunderten von Findings. Hier kommt dieses Tool ins Spiel - es gibt dir eine interaktive Terminal-UI zum Durchsuchen, Filtern, Inspizieren und Beheben dieser Findings.

## Features

- **Horizontal-Split-Layout** - Findings-Tabelle links, Quellcode mit Syntax-Highlighting rechts
- **Findings durchsuchen** in einer filterbaren Tabelle mit Severity-Farben
- **Quellcode-Ansicht** mit automatischem Sprung zur betroffenen Zeile
- **`jb inspectcode` direkt starten** aus der TUI heraus mit Live-Log und Fortschrittsanzeige
- **Git-Commit-Modus** - nur geänderte Dateien seit einem Commit scannen (`--commit HEAD~1`)
- **Auto-Fix** für 11 Issue-Typen mit Diff-Vorschau vor dem Anwenden
- **History** - letzte Scan-Parameter merken und wiederverwenden
- **Top 10 Chart** - häufigste Finding-Typen, Kategorien und Dateien auf einen Blick
- **31 Retro-Themes** - via Theme-Picker (Ctrl+P), siehe [textual-themes](https://github.com/michaelblaess/textual-themes)
- **Whitelist** - bekannte Issues per `whitelist.json` ignorieren, Ein/Aus-Toggle und Hinzufügen direkt in der TUI
- **Settings-Persistenz** - Theme, Log-Höhe und Sichtbarkeit werden gespeichert
- **Mehrsprachig** - Deutsch und Englisch, umschaltbar mit `--lang en`
- **.sln und .csproj** - beide Projekttypen werden unterstützt
- **XML und SARIF/JSON** - beide InspectCode-Ausgabeformate werden automatisch erkannt

## Voraussetzungen

- **Python 3.10+**
- **JetBrains CLI Tools** (`jb inspectcode`) - installieren mit:
  ```bash
  dotnet tool install -g JetBrains.ReSharper.GlobalTools
  ```

## Installation

### One-Click-Install (Standalone, kein Python nötig)

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/inspectcode-tui/main/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/inspectcode-tui/main/install.sh | bash
```

### Aus Quellcode (Python 3.10+)

```bash
git clone https://github.com/michaelblaess/inspectcode-tui.git
cd inspectcode-tui
pip install -e .
```

## Verwendung

```bash
# Live-Scan einer Solution starten
inspectcode-tui "C:\Pfad\zu\MeineSolution.sln"

# Einzelnes .csproj scannen
inspectcode-tui "C:\Pfad\zu\MeinProjekt.csproj"

# Nur ein bestimmtes Projekt innerhalb der Solution scannen
inspectcode-tui "MeineSolution.sln" --project="MeinProjekt"

# Nur geänderte Dateien seit letztem Commit scannen (Git-Modus)
inspectcode-tui "MeineSolution.sln" --commit HEAD~1

# Vorhandene Report-Datei laden (kein Scan nötig)
inspectcode-tui --xml="C:\Temp\inspectcode-results.xml"

# Nach minimaler Severity filtern
inspectcode-tui --xml="report.xml" --severity=ERROR

# Vor dem Scan bauen (Standard: --no-build)
inspectcode-tui "MeineSolution.sln" --build

# Englische Oberfläche
inspectcode-tui "MeineSolution.sln" --lang en

# Ohne Argumente starten (History-Auswahl)
inspectcode-tui
```

> **Tipp:** Schließe Visual Studio bevor du einen Live-Scan startest, um Dateisperren zu vermeiden.
> Die gewählte Sprache wird gespeichert und beim nächsten Start automatisch verwendet.

## Tastenkürzel

| Taste     | Aktion                                  |
|-----------|-----------------------------------------|
| `s`       | Scan starten                            |
| `f`       | Fix anwenden (nur bei fixbaren Issues)  |
| `d`       | Diff-Vorschau (nur bei fixbaren Issues) |
| `w`       | Whitelist AN/AUS                        |
| `a`       | Finding zur Whitelist hinzufügen        |
| `j`       | JetBrains Wiki-Seite öffnen            |
| `h`       | History-Dialog                          |
| `o`       | Top-10-Chart                            |
| `r`       | Aktuelle Zeile kopieren                 |
| `t`       | Gesamte Tabelle kopieren               |
| `/`       | Filter fokussieren                      |
| `Escape`  | Filter leeren                           |
| `l`       | Log ein-/ausblenden                     |
| `+` / `-` | Log vergrößern / verkleinern           |
| `c`       | Log kopieren                            |
| `x`       | Log leeren                              |
| `i`       | Info/About                              |
| `Ctrl+P`  | Theme wechseln                          |
| `q`       | Beenden                                 |

## Automatisch behebbare Issue-Typen

| Issue-Typ | Fix |
|---|---|
| `RedundantUsingDirective` | Zeile entfernen |
| `UnusedVariable` | Zeile entfernen |
| `RedundantAssignment` | Zeile entfernen |
| `HeuristicUnreachableCode` | Zeile entfernen |
| `EmptyConstructor` | Konstruktor-Block entfernen |
| `RedundantBaseConstructorCall` | `: base()` entfernen |
| `RedundantDefaultMemberInitializer` | `= 0` / `= null` / `= false` / `= default` entfernen |
| `PossibleIntendedRethrow` | `throw ex;` durch `throw;` ersetzen |
| `RedundantBaseQualifier` | `base.` Prefix entfernen |
| `ConstantConditionalAccessQualifier` | `?.` durch `.` ersetzen |
| `StringIndexOfIsCultureSpecific.1` | `StringComparison.Ordinal` hinzufügen |

Weitere Fix-Strategien können in `src/inspectcode_tui/services/fixer.py` ergänzt werden.

## So funktioniert es

1. **InspectCode** analysiert deine .NET-Solution und schreibt einen Report (XML oder SARIF/JSON)
2. **inspectcode-tui** erkennt das Format automatisch und parst es in strukturierte `Finding`-Objekte
3. Findings werden in einer **DataTable** mit Severity-Farben und Filterung angezeigt
4. Beim Navigieren wird automatisch der **Quellcode** mit markierter Zeile rechts angezeigt
5. Für behebbare Issues kannst du den **Diff vorab ansehen** und den Fix per Tastendruck anwenden
6. Git ist dein Sicherheitsnetz - alle Änderungen können jederzeit mit `git checkout` rückgängig gemacht werden

## Projektstruktur

```
src/inspectcode_tui/
├── __main__.py              # CLI entry point (argparse, --lang)
├── app.py                   # Main Textual app (horizontal split, keybindings)
├── app.tcss                 # Stylesheet
├── i18n.py                  # Internationalization (de/en)
├── locale/
│   ├── de.json              # German language pack
│   └── en.json              # English language pack
├── models/
│   ├── finding.py           # Finding dataclass
│   ├── report.py            # Report parser (XML + SARIF/JSON)
│   ├── settings.py          # Persistent settings (~/.inspectcode-tui/)
│   └── history.py           # Scan history (~/.inspectcode-tui/)
├── widgets/
│   ├── findings_table.py    # Filterable DataTable with severity colors
│   ├── code_view.py         # Scrollable syntax-highlighted code display
│   └── summary_panel.py     # Severity counters
├── screens/
│   ├── confirm_fix.py       # Modal: confirm fix with diff preview
│   ├── diff_view.py         # Modal: diff preview
│   ├── history.py           # Modal: scan history selection
│   ├── top_findings.py      # Modal: top 10 bar charts
│   └── about.py             # Modal: about dialog
└── services/
    ├── inspector.py         # jb inspectcode subprocess runner + git diff
    └── fixer.py             # Auto-fix logic (11 issue types)
```

## Haftungsausschluss

Dieses Projekt ist ein **unabhängiges, inoffizielles Tool** und steht in **keiner Verbindung zu JetBrains s.r.o.** - es wird von JetBrains weder unterstützt noch gefördert oder gesponsert.

**JetBrains**, **ReSharper** und **InspectCode** sind Marken oder eingetragene Marken von [JetBrains s.r.o.](https://www.jetbrains.com/). Alle Produktnamen, Logos und Marken sind Eigentum ihrer jeweiligen Inhaber.

Dieses Tool stellt lediglich eine Terminal-Oberfläche zur Darstellung und Bearbeitung der Ausgaben von JetBrains InspectCode bereit. Es enthält, bündelt oder verteilt keine JetBrains-Software. Die [JetBrains ReSharper Command Line Tools](https://www.jetbrains.com/help/resharper/ReSharper_Command_Line_Tools.html) müssen separat installiert werden, und Nutzer müssen die Lizenzbedingungen von JetBrains selbst einhalten.

## Lizenz

Apache License 2.0 - siehe [LICENSE](LICENSE)
