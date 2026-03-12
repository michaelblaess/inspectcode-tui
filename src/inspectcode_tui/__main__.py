"""Entry Point fuer InspectCode TUI."""

from __future__ import annotations

import argparse
import sys

from .i18n import load_locale, t
from .models.settings import Settings


def main() -> None:
    """Haupteinstiegspunkt fuer die CLI."""
    # Sprache VOR argparse laden, damit auch die Hilfe-Texte uebersetzt sind
    settings = Settings.load()
    lang = settings.language
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--lang" and i + 1 < len(sys.argv[1:]):
            lang = sys.argv[i + 2]
            break
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1]
            break
    load_locale(lang)

    # Sprache in Settings persistieren
    if lang != settings.language:
        settings.language = lang
        settings.save()

    parser = argparse.ArgumentParser(
        prog="inspectcode-tui",
        description=t("cli.description"),
    )

    parser.add_argument(
        "solution",
        nargs="?",
        default="",
        help=t("cli.solution_help"),
    )
    parser.add_argument(
        "--project",
        default="",
        help=t("cli.project_help"),
    )
    parser.add_argument(
        "--xml",
        default="",
        help=t("cli.xml_help"),
    )
    parser.add_argument(
        "--severity",
        default="WARNING",
        choices=["HINT", "SUGGESTION", "WARNING", "ERROR"],
        help=t("cli.severity_help"),
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        default=True,
        help=t("cli.no_build_help"),
    )
    parser.add_argument(
        "--build",
        action="store_true",
        default=False,
        help=t("cli.build_help"),
    )
    parser.add_argument(
        "--commit",
        default="",
        help=t("cli.commit_help"),
    )
    parser.add_argument(
        "--lang",
        default=lang,
        choices=["de", "en"],
        help=t("cli.lang_help"),
    )

    args = parser.parse_args()

    # Dateiendung validieren (ohne Argumente startet die App fuer History-Auswahl)
    if args.solution:
        lower = args.solution.lower()
        if not lower.endswith(".sln") and not lower.endswith(".csproj"):
            print(t("cli.invalid_file", path=args.solution))
            sys.exit(1)

    no_build = not args.build if args.build else args.no_build

    from .app import InspectCodeApp

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
