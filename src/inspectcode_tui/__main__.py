"""Entry Point fuer InspectCode TUI."""

from __future__ import annotations

import argparse
import sys

from .app import InspectCodeApp


def main() -> None:
    """Haupteinstiegspunkt fuer die CLI."""
    parser = argparse.ArgumentParser(
        prog="inspectcode-tui",
        description="TUI fuer JetBrains InspectCode Ergebnisse",
    )

    parser.add_argument(
        "solution",
        nargs="?",
        default="",
        help="Pfad zur .sln- oder .csproj-Datei",
    )
    parser.add_argument(
        "--project",
        default="",
        help="Nur bestimmtes Projekt scannen",
    )
    parser.add_argument(
        "--xml",
        default="",
        help="Vorhandene Report-Datei laden (XML oder SARIF/JSON)",
    )
    parser.add_argument(
        "--severity",
        default="WARNING",
        choices=["HINT", "SUGGESTION", "WARNING", "ERROR"],
        help="Minimale Severity (default: WARNING)",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        default=True,
        help="Solution nicht bauen (default: true)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        default=False,
        help="Solution vor dem Scan bauen",
    )
    parser.add_argument(
        "--commit",
        default="",
        help="Git-Commit-Referenz: nur geaenderte Dateien seit diesem Commit scannen (z.B. HEAD~1, main, abc1234)",
    )

    args = parser.parse_args()

    # Dateiendung validieren (ohne Argumente startet die App fuer History-Auswahl)
    if args.solution:
        lower = args.solution.lower()
        if not lower.endswith(".sln") and not lower.endswith(".csproj"):
            print(f"Fehler: '{args.solution}' ist keine .sln- oder .csproj-Datei!")
            sys.exit(1)

    no_build = not args.build if args.build else args.no_build

    app = InspectCodeApp(
        solution_path=args.solution or "",
        project=args.project,
        xml_path=args.xml,
        severity=args.severity,
        no_build=no_build,
        commit=args.commit,
    )
    app.run()


if __name__ == "__main__":
    main()
