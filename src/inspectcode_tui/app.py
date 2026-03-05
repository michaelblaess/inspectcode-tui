"""Hauptanwendung fuer InspectCode TUI."""

from __future__ import annotations

import json
import time
from fnmatch import fnmatch
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import (
    Footer,
    Header,
    RichLog,
    Static,
)

from textual_themes import register_all

from . import __version__, __year__
from .models.finding import Finding
from .models.history import History, HistoryEntry
from .models.report import Report
from .models.settings import Settings
from .screens.confirm_fix import ConfirmFixScreen, FixDecision
from .screens.diff_view import DiffViewScreen
from .services.fixer import Fixer
from .services.inspector import InspectOptions, get_git_changed_files, run_inspection
from .widgets.code_view import CodeView
from .widgets.findings_table import FindingsTable
from .widgets.summary_panel import SummaryPanel


# Log-Hoehe: min/max/step (Zeilen)
LOG_HEIGHT_MIN = 5
LOG_HEIGHT_MAX = 30
LOG_HEIGHT_STEP = 3

# Fortschrittsbalken-Breite
_BAR_WIDTH = 20


class InspectCodeApp(App):
    """TUI-Anwendung fuer JetBrains InspectCode Ergebnisse."""

    CSS_PATH = "app.tcss"
    TITLE = f"InspectCode TUI v{__version__} ({__year__})"

    BINDINGS = [
        Binding("q", "quit", "Beenden"),
        Binding("s", "run_scan", "Scan"),
        Binding("f", "fix_selected", "Fix"),
        Binding("d", "show_diff", "Diff"),
        Binding("h", "show_history", "History"),
        Binding("t", "copy_table", "Tabelle kopieren"),
        Binding("o", "show_top_findings", "Top 10"),
        Binding("l", "toggle_log", "Log"),
        Binding("plus", "log_bigger", "Log +", key_display="+"),
        Binding("minus", "log_smaller", "Log -", key_display="-"),
        Binding("slash", "focus_filter", "Filter", key_display="/"),
        Binding("escape", "clear_filter", "Filter leeren", show=False),
        Binding("r", "copy_row", "Row kopieren"),
        Binding("w", "toggle_whitelist", "Whitelist AN"),
        Binding("a", "add_to_whitelist", "Whitelisten"),
        Binding("j", "open_wiki", "JetBrains Wiki"),
        Binding("c", "copy_log", "Log kopieren"),
        Binding("x", "clear_log", "Log leeren"),
        Binding("i", "show_about", "Info"),
    ]

    def __init__(
        self,
        solution_path: str = "",
        project: str = "",
        xml_path: str = "",
        severity: str = "WARNING",
        no_build: bool = True,
        commit: str = "",
    ) -> None:
        super().__init__()

        # Retro-Themes registrieren
        register_all(self)

        # Persistierte Einstellungen laden
        self._settings = Settings.load()

        self.solution_path = solution_path
        self.project = project
        self.xml_path = xml_path
        self.severity = severity
        self.no_build = no_build
        self.commit = commit
        self._findings: list[Finding] = []
        self._report: Report | None = None
        self._fixer: Fixer | None = None
        self._current_finding: Finding | None = None
        self._log_lines: list[str] = []
        self._scan_running: bool = False
        self._scan_start_time: float = 0
        self._scan_progress_timer: Timer | None = None
        self._git_changed_files: list[str] = []
        self._whitelist_active: bool = True
        self._all_findings: list[Finding] = []

        # Theme aus Settings uebernehmen
        self.theme = self._settings.theme

    def compose(self) -> ComposeResult:
        """Erstellt das UI-Layout (Horizontal-Split)."""
        yield Header()
        yield SummaryPanel(id="summary")

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield FindingsTable(id="findings-table")
                yield RichLog(id="scan-log", highlight=True, markup=True)

            with Vertical(id="right-panel"):
                yield Static("Keine Datei geladen", id="code-file-label")
                yield CodeView(id="code-display")

        yield Footer()

    def on_mount(self) -> None:
        """Initialisierung nach dem Starten."""
        # Log-Hoehe und Sichtbarkeit aus Settings wiederherstellen
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.styles.height = self._settings.log_height

        if not self._settings.log_visible:
            log_widget.add_class("hidden")

        # Versionsinfo
        self._write_log(f"[bold]InspectCode TUI v{__version__}[/bold]")

        if self.xml_path:
            self._load_report(self.xml_path)
        elif self.solution_path:
            self._write_log(f"Solution: {self.solution_path}")
            self._write_log("[dim]Druecke [bold]s[/bold] um den Scan zu starten.[/dim]")
        else:
            self._write_log("[dim]Keine Solution angegeben.[/dim]")
            self._write_log("[dim]Druecke [bold]h[/bold] fuer History oder starte mit einer .sln/.csproj-Datei.[/dim]")

    def _load_report(self, report_path: str) -> None:
        """Laedt eine vorhandene Report-Datei (XML oder SARIF/JSON).

        Args:
            report_path: Pfad zur Report-Datei.
        """
        try:
            self._report = Report(report_path)
            self._findings = self._report.parse()
        except Exception as e:
            self._write_log(f"[red]Fehler beim Laden: {e}[/red]")
            self.notify(f"Fehler: {e}", severity="error")
            return

        # Solution-Dir ermitteln fuer Fixer
        if self.solution_path:
            sol_dir = Path(self.solution_path).parent
        else:
            sol_dir = Path(report_path).parent
        self._fixer = Fixer(sol_dir)

        # Filter nach Severity
        if self.severity:
            self._findings = self._report.filter_by_severity(self.severity)

        # Git-Commit-Modus: Findings auf geaenderte Dateien filtern
        if self._git_changed_files:
            before_count = len(self._findings)
            self._findings = self._report.filter_by_files(self._git_changed_files)
            self._write_log(
                f"Git-Filter: {len(self._findings)} von {before_count} Findings "
                f"in {len(self._git_changed_files)} geaenderten Dateien"
            )

        # Alle Findings (vor Whitelist) merken
        self._all_findings = list(self._findings)

        # Whitelist anwenden
        if self._whitelist_active:
            whitelist_count = self._apply_whitelist()
            if whitelist_count > 0:
                self._write_log(
                    f"[dim]Whitelist: {whitelist_count} Findings ignoriert[/dim]"
                )

        self._refresh_findings_ui(report_path)

    def _refresh_findings_ui(self, report_path: str = "") -> None:
        """Aktualisiert die Findings-Tabelle und Summary."""
        table = self.query_one("#findings-table", FindingsTable)
        table.load_findings(self._findings)

        solution_name = self._report.solution_name if self._report else ""
        summary = self.query_one("#summary", SummaryPanel)
        summary.update_findings(self._findings, solution_name)

        if report_path:
            self._write_log(f"[green]Geladen: {report_path}[/green]")
            self._write_log(f"Solution: {solution_name}")
        self._write_log(f"Findings: {len(self._findings)}")

        self.sub_title = f"{solution_name} - {len(self._findings)} Findings"

    def _apply_whitelist(self) -> int:
        """Entfernt Findings die in der whitelist.json stehen.

        Sucht die whitelist.json im Arbeitsverzeichnis und neben der Report-Datei.
        Matcht auf type_id (exakt) und message (Wildcard mit fnmatch).

        Returns:
            Anzahl der entfernten Findings.
        """
        whitelist_path = self._find_whitelist()
        if whitelist_path is None:
            return 0

        try:
            data = json.loads(whitelist_path.read_text(encoding="utf-8"))
            rules = data.get("rules", [])
        except Exception:
            return 0

        if not rules:
            return 0

        before = len(self._findings)
        filtered: list[Finding] = []
        for f in self._findings:
            skip = False
            for rule in rules:
                rule_type = rule.get("type_id", "")
                rule_msg = rule.get("message", "")
                if rule_type and f.type_id != rule_type:
                    continue
                if rule_msg and not fnmatch(f.message, f"*{rule_msg}*"):
                    continue
                skip = True
                break
            if not skip:
                filtered.append(f)

        self._findings = filtered
        return before - len(filtered)

    def _find_whitelist(self) -> Path | None:
        """Sucht whitelist.json im CWD, neben der Report-Datei und neben der App."""
        candidates = [
            Path.cwd() / "whitelist.json",
            Path(__file__).resolve().parent.parent.parent / "whitelist.json",
        ]
        if self._report:
            candidates.append(self._report.report_path.parent / "whitelist.json")
        for p in candidates:
            if p.is_file():
                return p
        return None

    @work(exclusive=True)
    async def action_run_scan(self) -> None:
        """Startet einen neuen InspectCode-Scan."""
        if not self.solution_path:
            self.notify("Kein Solution-Pfad angegeben!", severity="error")
            return

        self._scan_running = True
        self._scan_start_time = time.monotonic()
        self.refresh_bindings()

        log = self.query_one("#scan-log", RichLog)
        log.remove_class("hidden")
        log.clear()
        self._log_lines.clear()
        self._write_log("[bold]Scan wird gestartet...[/bold]")

        # Progress-Timer starten
        self._scan_progress_timer = self.set_interval(0.5, self._tick_scan_progress)

        # Git-Commit-Modus: geaenderte Dateien ermitteln
        include_files: list[str] = []
        if self.commit:
            sol_dir = Path(self.solution_path).parent
            self._write_log(f"[bold]Git-Modus: diff seit {self.commit}[/bold]")
            self._git_changed_files = await get_git_changed_files(
                sol_dir, self.commit, on_output=self._write_log,
            )
            if not self._git_changed_files:
                self._write_log("[yellow]Keine geaenderten .cs-Dateien gefunden.[/yellow]")
                self.notify("Keine geaenderten .cs-Dateien!", severity="warning")
                self._stop_scan()
                return
            include_files = list(self._git_changed_files)

        options = InspectOptions(
            solution_path=self.solution_path,
            project=self.project,
            severity=self.severity,
            no_build=self.no_build,
            commit=self.commit,
            include_files=include_files,
        )

        # History-Eintrag speichern
        try:
            history_entry = HistoryEntry(
                solution_path=self.solution_path,
                project=self.project,
                severity=self.severity,
                no_build=self.no_build,
                commit=self.commit,
            )
            History.add(history_entry)
            self._write_log("[dim]History aktualisiert[/dim]")
        except Exception:
            pass

        def on_output(line: str) -> None:
            self._write_log(line)

        return_code, xml_path = await run_inspection(options, on_output=on_output)

        self._stop_scan()

        if return_code == 0:
            self._load_report(xml_path)
        else:
            self.notify(f"Scan fehlgeschlagen (Exit-Code: {return_code})", severity="error")

    def _stop_scan(self) -> None:
        """Stoppt den Scan und den Progress-Timer."""
        self._scan_running = False
        if self._scan_progress_timer is not None:
            self._scan_progress_timer.stop()
            self._scan_progress_timer = None

        # Dauer anzeigen
        if self._scan_start_time > 0:
            duration_ms = int((time.monotonic() - self._scan_start_time) * 1000)
            self.sub_title = f"Scan abgeschlossen in {_format_duration(duration_ms)}"
            self._scan_start_time = 0

        self.refresh_bindings()

    def _tick_scan_progress(self) -> None:
        """Timer-Callback: Aktualisiert den Fortschrittsbalken im Header."""
        elapsed = time.monotonic() - self._scan_start_time
        bar = _format_progress_bar(elapsed)
        duration = _format_duration(int(elapsed * 1000))
        self.sub_title = f"Scanning {bar} {duration}"

    def on_findings_table_finding_selected(
        self, event: FindingsTable.FindingSelected
    ) -> None:
        """Reagiert auf Doppelklick/Enter auf ein Finding."""
        self._show_code(event.finding)

    def on_findings_table_finding_highlighted(
        self, event: FindingsTable.FindingHighlighted
    ) -> None:
        """Aktualisiert Code-Ansicht bei Cursor-Bewegung (automatisch rechts)."""
        self._current_finding = event.finding
        self._show_code(event.finding)
        self.refresh_bindings()

    def _show_code(self, finding: Finding) -> None:
        """Zeigt den Code eines Findings in der rechten Haelfte an.

        Args:
            finding: Das anzuzeigende Finding.
        """
        self._current_finding = finding

        # Dateipfad aufloesen
        if self._fixer:
            file_path = self._fixer._resolve_path(finding.file)
        elif self.solution_path:
            file_path = Path(self.solution_path).parent / finding.file
        else:
            file_path = Path(finding.file)

        # Code laden
        code_view = self.query_one("#code-display", CodeView)
        loaded = code_view.load_file(file_path, highlight_line=finding.line)

        # Datei-Label aktualisieren
        label = self.query_one("#code-file-label", Static)
        if loaded:
            label.update(f" {finding.file}:{finding.line}\n {finding.type_id}: {finding.message}")
        else:
            label.update(f" Datei nicht gefunden: {file_path}")

    def action_fix_selected(self) -> None:
        """Wendet einen Fix auf das ausgewaehlte Finding an."""
        finding = self._current_finding
        if not finding:
            self.notify("Kein Finding ausgewaehlt!", severity="warning")
            return

        if not self._fixer:
            self.notify("Kein Fixer konfiguriert!", severity="error")
            return

        if not self._fixer.can_fix(finding):
            self.notify(
                f"Kein automatischer Fix fuer '{finding.type_id}' verfuegbar.",
                severity="warning",
            )
            return

        preview = self._fixer.preview_fix(finding)
        if not preview.success:
            self.notify(preview.message, severity="error")
            return

        self.push_screen(
            ConfirmFixScreen(finding, preview),
            self._on_fix_decision,
        )

    def _on_fix_decision(self, decision: FixDecision) -> None:
        """Callback nach der Fix-Entscheidung.

        Args:
            decision: Entscheidung des Benutzers.
        """
        if not decision.confirmed:
            self.notify("Fix abgebrochen.")
            return

        finding = self._current_finding
        if not finding or not self._fixer:
            return

        result = self._fixer.apply_fix(finding)

        if result.success:
            self.notify(result.message, severity="information")
            self._write_log(f"[green]{result.message}[/green]")

            # Code-Ansicht aktualisieren
            self._show_code(finding)
        else:
            self.notify(result.message, severity="error")
            self._write_log(f"[red]{result.message}[/red]")

    def action_show_diff(self) -> None:
        """Zeigt einen Diff fuer das ausgewaehlte Finding."""
        finding = self._current_finding
        if not finding:
            self.notify("Kein Finding ausgewaehlt!", severity="warning")
            return

        if not self._fixer:
            self.notify("Kein Fixer konfiguriert!", severity="error")
            return

        preview = self._fixer.preview_fix(finding)
        if not preview.success or not preview.old_content:
            self.notify("Keine Diff-Vorschau verfuegbar.", severity="warning")
            return

        self.push_screen(
            DiffViewScreen(
                preview.old_content,
                preview.new_content,
                title=f"Diff: {finding.type_id} in {finding.filename}:{finding.line}",
            )
        )

    def action_show_history(self) -> None:
        """Zeigt die Scan-History und laedt bei Auswahl die Parameter."""
        from .screens.history import HistoryScreen
        self.push_screen(HistoryScreen(), callback=self._on_history_selected)

    def _on_history_selected(self, entry: HistoryEntry | None) -> None:
        """Verarbeitet die Auswahl eines History-Eintrags.

        Uebernimmt alle Parameter des Eintrags.
        Der Scan wird NICHT automatisch gestartet (User startet mit "r").

        Args:
            entry: Der ausgewaehlte HistoryEntry oder None.
        """
        if entry is None:
            return

        # Parameter uebernehmen
        self.solution_path = entry.solution_path
        self.project = entry.project
        self.severity = entry.severity
        self.no_build = entry.no_build
        self.commit = entry.commit

        self._write_log("[bold]History: Parameter uebernommen[/bold]")
        self._write_log(f"Solution: {self.solution_path}")
        params = [f"--severity {self.severity}"]
        if self.project:
            params.append(f"--project {self.project}")
        if not self.no_build:
            params.append("--build")
        if self.commit:
            params.append(f"--commit {self.commit}")
        self._write_log(f"Parameter: {' '.join(params)}")
        self._write_log("[dim]Scan mit 's' starten[/dim]")

    def action_show_top_findings(self) -> None:
        """Zeigt den Top-10-Findings Dialog."""
        if not self._findings:
            self.notify("Keine Findings vorhanden!", severity="warning")
            return

        from .screens.top_findings import TopFindingsScreen
        self.push_screen(TopFindingsScreen(self._findings))

    def action_toggle_log(self) -> None:
        """Blendet den Log-Bereich ein/aus."""
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.toggle_class("hidden")

        # Sichtbarkeit persistent speichern
        self._settings.log_visible = not log_widget.has_class("hidden")
        self._settings.save()

    def action_log_bigger(self) -> None:
        """Vergroessert den Log-Bereich."""
        new_height = min(self._settings.log_height + LOG_HEIGHT_STEP, LOG_HEIGHT_MAX)
        self._settings.log_height = new_height
        self._settings.save()

        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.styles.height = new_height

    def action_log_smaller(self) -> None:
        """Verkleinert den Log-Bereich."""
        new_height = max(self._settings.log_height - LOG_HEIGHT_STEP, LOG_HEIGHT_MIN)
        self._settings.log_height = new_height
        self._settings.save()

        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.styles.height = new_height

    def action_focus_filter(self) -> None:
        """Fokussiert das Filter-Eingabefeld."""
        try:
            from textual.widgets import Input
            filter_input = self.query_one("#filter-bar", Input)
            filter_input.focus()
        except Exception:
            pass

    def action_clear_filter(self) -> None:
        """Leert den Filter."""
        try:
            from textual.widgets import Input
            filter_input = self.query_one("#filter-bar", Input)
            filter_input.value = ""
        except Exception:
            pass

    def action_copy_row(self) -> None:
        """Kopiert das aktuelle Finding als Text in die Zwischenablage."""
        finding = self._current_finding
        if not finding:
            self.notify("Kein Finding ausgewaehlt!", severity="warning")
            return

        text = f"{finding.file}:{finding.line}\t{finding.severity}\t{finding.type_id}\t{finding.message}"
        self.copy_to_clipboard(text)
        self.notify(f"Row kopiert: {finding.filename}:{finding.line}")

    def action_copy_table(self) -> None:
        """Kopiert die gesamte Findings-Tabelle als Tab-getrennten Text in die Zwischenablage."""
        if not self._findings:
            self.notify("Keine Findings vorhanden!", severity="warning")
            return

        lines = ["Datei\tZeile\tSeverity\tKategorie\tTyp\tNachricht"]
        for finding in self._findings:
            lines.append(
                f"{finding.file}\t{finding.line}\t{finding.severity}\t"
                f"{finding.category}\t{finding.type_id}\t{finding.message}"
            )

        text = "\n".join(lines)
        self.copy_to_clipboard(text)
        self.notify(f"Tabelle kopiert ({len(self._findings)} Findings)")

    def action_toggle_whitelist(self) -> None:
        """Schaltet die Whitelist an/aus und aktualisiert die Findings."""
        import dataclasses

        self._whitelist_active = not self._whitelist_active

        if self._whitelist_active:
            # Whitelist anwenden: von allen Findings neu filtern
            self._findings = list(self._all_findings)
            count = self._apply_whitelist()
            self._write_log(f"[green]Whitelist AN[/green] ({count} Findings ignoriert)")
        else:
            # Whitelist aus: alle Findings zeigen
            self._findings = list(self._all_findings)
            self._write_log("[yellow]Whitelist AUS[/yellow]")

        # Binding-Label aktualisieren
        label = "Whitelist AN" if self._whitelist_active else "Whitelist AUS"
        bindings_list = self._bindings.key_to_bindings.get("w", [])
        for i, binding in enumerate(bindings_list):
            if binding.action == "toggle_whitelist":
                self._bindings.key_to_bindings["w"][i] = dataclasses.replace(
                    binding, description=label
                )
                break
        self.refresh_bindings()

        self._refresh_findings_ui()

    def action_add_to_whitelist(self) -> None:
        """Fuegt das aktuell markierte Finding zur Whitelist hinzu."""
        finding = self._current_finding
        if not finding:
            self.notify("Kein Finding ausgewaehlt!", severity="warning")
            return

        whitelist_path = self._find_whitelist()
        if whitelist_path is None:
            # Neue whitelist.json im CWD erstellen
            whitelist_path = Path.cwd() / "whitelist.json"

        # Bestehende Whitelist laden oder neue erstellen
        if whitelist_path.is_file():
            try:
                data = json.loads(whitelist_path.read_text(encoding="utf-8"))
            except Exception:
                data = {"description": "Whitelist", "rules": []}
        else:
            data = {"description": "Whitelist", "rules": []}

        rules = data.get("rules", [])

        # Pruefen ob Regel schon existiert
        new_rule = {"type_id": finding.type_id}
        for rule in rules:
            if rule.get("type_id") == finding.type_id and not rule.get("message"):
                self.notify(f"'{finding.type_id}' ist bereits in der Whitelist")
                return

        rules.append(new_rule)
        data["rules"] = rules

        # Speichern
        whitelist_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        self._write_log(
            f"[green]Whitelist: '{finding.type_id}' hinzugefuegt → {whitelist_path}[/green]"
        )
        self.notify(f"'{finding.type_id}' zur Whitelist hinzugefuegt")

        # Whitelist sofort neu anwenden
        if self._whitelist_active and self._all_findings:
            self._findings = list(self._all_findings)
            count = self._apply_whitelist()
            self._write_log(f"[dim]Whitelist: {count} Findings ignoriert[/dim]")
            self._refresh_findings_ui()

    def action_open_wiki(self) -> None:
        """Oeffnet die JetBrains Wiki-Seite zum aktuellen Finding im Browser."""
        import webbrowser

        finding = self._current_finding
        if not finding:
            self.notify("Kein Finding ausgewaehlt!", severity="warning")
            return

        if finding.wiki_url:
            url = finding.wiki_url
        else:
            # Fallback: JetBrains Suche nach der TypeId
            url = f"https://www.jetbrains.com/help/resharper/Reference__Code_Inspections_CSHARP.html#{finding.type_id}"

        webbrowser.open(url)
        self.notify(f"Wiki: {finding.type_id}")

    def action_copy_log(self) -> None:
        """Kopiert das Log in die Zwischenablage."""
        if not self._log_lines:
            self.notify("Log ist leer.", severity="warning")
            return
        text = "\n".join(self._log_lines)
        self.copy_to_clipboard(text)
        self.notify(f"Log kopiert ({len(self._log_lines)} Zeilen)")

    def action_clear_log(self) -> None:
        """Leert das Log."""
        self._log_lines.clear()
        self.query_one("#scan-log", RichLog).clear()
        self.notify("Log geleert.")

    def action_show_about(self) -> None:
        """Zeigt den About-Dialog an."""
        from .screens.about import AboutScreen
        self.push_screen(AboutScreen())

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Steuert Sichtbarkeit von Bindings kontextabhaengig.

        Args:
            action: Name der Aktion.
            parameters: Aktionsparameter.

        Returns:
            True wenn sichtbar, None wenn versteckt.
        """
        # Waehrend Scan: bestimmte Aktionen ausblenden
        if self._scan_running and action in (
            "show_history", "run_scan", "show_top_findings",
            "fix_selected", "show_diff",
        ):
            return None

        # Fix/Diff nur anzeigen wenn aktuelles Finding fixbar ist
        if action in ("fix_selected", "show_diff"):
            finding = self._current_finding
            if not finding or not self._fixer or not self._fixer.can_fix(finding):
                return None

        return True

    def watch_theme(self, theme_name: str) -> None:
        """Speichert das Theme bei Aenderung persistent.

        Args:
            theme_name: Name des neuen Themes.
        """
        self._settings.theme = theme_name
        self._settings.save()

    def _write_log(self, line: str) -> None:
        """Schreibt eine Zeile ins Log-Widget und in den Puffer.

        Args:
            line: Log-Nachricht (kann Rich-Markup enthalten).
        """
        self._log_lines.append(line)
        try:
            self.query_one("#scan-log", RichLog).write(line)
        except Exception:
            pass


def _format_progress_bar(elapsed_s: float) -> str:
    """Erzeugt einen animierten Unicode-Fortschrittsbalken.

    Da InspectCode keinen Prozentwert liefert, zeigen wir eine
    laufende Animation statt eines echten Fortschritts.

    Args:
        elapsed_s: Vergangene Zeit in Sekunden.

    Returns:
        String mit animierten Segmenten.
    """
    # Laufende Animation: "Bounce"-Effekt
    pos = int(elapsed_s * 2) % (_BAR_WIDTH * 2)
    if pos >= _BAR_WIDTH:
        pos = _BAR_WIDTH * 2 - pos - 1

    segments = []
    for i in range(_BAR_WIDTH):
        if abs(i - pos) <= 1:
            segments.append("\u2588")
        else:
            segments.append("\u2591")
    return "".join(segments)


def _format_duration(duration_ms: int) -> str:
    """Formatiert eine Dauer in lesbarer Form.

    Unter 60s: "12.3s", ab 60s: "2m 30s", ab 60m: "1h 5m 30s".

    Args:
        duration_ms: Dauer in Millisekunden.

    Returns:
        Formatierter String.
    """
    total_s = duration_ms / 1000
    if total_s < 60:
        return f"{total_s:.1f}s"
    minutes = int(total_s // 60)
    seconds = int(total_s % 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {seconds}s"
