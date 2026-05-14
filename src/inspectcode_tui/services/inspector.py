"""Service fuer das Ausfuehren von jb inspectcode."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import t


@dataclass
class InspectOptions:
    """Optionen fuer den InspectCode-Lauf.

    Attributes:
        solution_path: Pfad zur .sln- oder .csproj-Datei.
        project: Optionaler Projektname.
        severity: Minimale Severity.
        no_build: Solution nicht bauen.
        output_path: Pfad fuer die Ausgabedatei.
        commit: Git-Commit-Referenz (leer = kein Git-Modus).
        include_files: Liste von Dateien fuer --include (Semikolon-getrennt).
    """

    solution_path: str
    project: str = ""
    severity: str = "WARNING"
    no_build: bool = True
    output_path: str = ""
    commit: str = ""
    include_files: list[str] = field(default_factory=list)

    def build_args(self) -> list[str]:
        """Erstellt die Kommandozeilen-Argumente fuer jb inspectcode.

        Returns:
            Liste der Argumente.
        """
        if not self.output_path:
            self.output_path = str(Path(tempfile.gettempdir()) / "inspectcode-tui-results.xml")

        args = [
            "jb",
            "inspectcode",
            self.solution_path,
            f"--output={self.output_path}",
            f"--severity={self.severity}",
        ]

        if self.project:
            args.append(f"--project={self.project}")

        if self.no_build:
            args.append("--no-build")

        # XML-Format erzwingen (kleiner und schneller als SARIF)
        args.append("--format=Xml")

        # --include: nur C#-Dateien scannen, oder spezifische Dateien (Git-Modus)
        if self.include_files:
            include_str = ";".join(self.include_files)
            args.append(f"--include={include_str}")
        else:
            args.append("--include=**/*.cs;**/*.cshtml")

        # Standard-Ausschluesse
        args.append(
            "--exclude="
            "**/obj/**;**/bin/**;**/node_modules/**;"
            "**/Migrations/**;**/*.generated.cs;**/*.designer.cs;"
            "**/packages/**;**/.vs/**;**/TestResults/**"
        )

        # Alle verfuegbaren Kerne nutzen
        args.append("--jobs=0")

        # Cache-Verzeichnis: beschleunigt Folge-Scans erheblich
        cache_dir = Path(tempfile.gettempdir()) / "inspectcode-tui-cache"
        args.append(f"--caches-home={cache_dir}")

        # Keine Update-Pruefung bei jedem Lauf
        args.append("--no-updates")

        # Telemetrie deaktivieren
        args.append("--telemetry-optout")

        return args


async def run_inspection(
    options: InspectOptions,
    on_output: Callable[[str], None] | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> tuple[int, str]:
    """Fuehrt jb inspectcode als async Subprocess aus.

    Args:
        options: Optionen fuer den InspectCode-Lauf.
        on_output: Callback fuer jede Zeile der Ausgabe.
        on_progress: Callback fuer Fortschritt (0-100).

    Returns:
        Tuple aus (Return-Code, Pfad zur XML-Datei).
    """
    args = options.build_args()

    if on_output:
        on_output(f"$ {' '.join(args)}")
        on_output("")

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    line_count = 0
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace").rstrip()
        line_count += 1

        if on_output:
            on_output(decoded)

        if on_progress:
            # InspectCode gibt keine Prozentzahlen aus,
            # daher schaetzen wir den Fortschritt
            on_progress(min(line_count, 95))

    return_code = await process.wait()

    if on_progress:
        on_progress(100)

    if on_output:
        on_output("")
        if return_code == 0:
            on_output(t("inspector.scan_completed", path=options.output_path))
        else:
            on_output(t("inspector.scan_failed", code=return_code))

    return return_code, options.output_path


async def get_git_changed_files(
    solution_dir: str | Path,
    commit: str,
    on_output: Callable[[str], None] | None = None,
) -> list[str]:
    """Ermittelt per git diff die geaenderten C#-Dateien seit einem Commit.

    Filtert auf .cs und .cshtml Dateien (nur Dateien mit C#-Code).

    Args:
        solution_dir: Verzeichnis der Solution (Arbeitsverzeichnis fuer git).
        commit: Git-Commit-Referenz (z.B. HEAD~1, abc1234, main).
        on_output: Optionaler Callback fuer Log-Ausgabe.

    Returns:
        Liste der geaenderten C#-Dateipfade (relativ zum Repo-Root).
        Leere Liste bei Fehler.
    """
    solution_dir = str(solution_dir)

    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "--name-only",
            commit,
            cwd=solution_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            if on_output:
                on_output(t("inspector.git_failed", error=error_msg))
            return []

        all_files = stdout.decode("utf-8", errors="replace").strip().splitlines()

        # Nur C#-Dateien filtern (.cs und .cshtml)
        cs_extensions = (".cs", ".cshtml")
        cs_files = [f for f in all_files if f.lower().endswith(cs_extensions)]

        if on_output:
            on_output(t("inspector.git_stats", commit=commit, total=len(all_files), cs=len(cs_files)))
            for cs_file in cs_files:
                on_output(f"  {cs_file}")

        return cs_files

    except FileNotFoundError:
        if on_output:
            on_output(t("inspector.git_not_found"))
        return []
    except Exception as exc:
        if on_output:
            on_output(t("inspector.git_error", error=exc))
        return []
