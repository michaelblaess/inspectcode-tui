"""Headless-Start der App mit einem Beispielreport.

Prueft den kompletten Weg Report-Datei -> Parser -> Severity-Filter ->
Tabelle und Zusammenfassung, ohne Terminal und ohne jb inspectcode.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import DataTable, Input, Static

from inspectcode_tui.app import InspectCodeApp
from inspectcode_tui.i18n import t
from inspectcode_tui.widgets.findings_table import FindingsTable
from inspectcode_tui.widgets.summary_panel import SummaryPanel


@pytest.fixture(autouse=True)
def _ohne_repo_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Die whitelist.json im Repo-Root wuerde sonst Findings ausblenden."""
    monkeypatch.setattr(InspectCodeApp, "_find_whitelist", lambda self: None)


def test_app_zeigt_findings_aus_xml_report(fixtures_dir: Path) -> None:
    report = fixtures_dir / "report.xml"

    async def drive() -> tuple[int, str, str, str]:
        app = InspectCodeApp(xml_path=str(report), severity="HINT")
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            table = app.query_one("#findings-data", DataTable)
            first_file = str(table.get_row_at(0)[2])
            summary = str(app.query_one("#summary", SummaryPanel).render())
            count_label = str(app.query_one("#findings-count", Static).render())
            return table.row_count, first_file, summary, f"{app.sub_title}|{count_label}"

    rows, first_file, summary, labels = asyncio.run(drive())

    assert rows == 6
    assert first_file == "Demo.Core\\Services\\OrderService.cs"
    assert "Demo.sln" in summary
    assert "ERROR: 1" in summary
    assert t("app.subtitle_findings", name="Demo.sln", count=6) in labels
    assert t("table.count", count=6).strip() in labels


def test_app_wendet_severity_vom_start_an(fixtures_dir: Path) -> None:
    report = fixtures_dir / "report.sarif.json"

    async def drive() -> int:
        app = InspectCodeApp(xml_path=str(report), severity="ERROR")
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            return app.query_one("#findings-data", DataTable).row_count

    # SARIF: 1x Regel-Default error, 1x result.level error, 1x warning
    assert asyncio.run(drive()) == 2


def test_filterzeile_schraenkt_tabelle_ein(fixtures_dir: Path) -> None:
    report = fixtures_dir / "report.xml"

    async def drive() -> tuple[int, int, int, int]:
        app = InspectCodeApp(xml_path=str(report), severity="HINT")
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            table = app.query_one("#findings-data", DataTable)
            findings_table = app.query_one("#findings-table", FindingsTable)

            # Volltextsuche ueber Datei, Meldung, Kategorie und Typ
            app.query_one("#filter-bar", Input).value = "order.cs"
            await pilot.pause()
            nach_text = table.row_count

            app.query_one("#filter-bar", Input).value = ""
            findings_table.set_severity_filter("warning")
            await pilot.pause()
            nach_severity = table.row_count

            findings_table.set_severity_filter("")
            findings_table.set_category_filter("redundancies")
            await pilot.pause()
            nach_kategorie = table.row_count

            findings_table.set_category_filter("")
            await pilot.pause()
            return nach_text, nach_severity, nach_kategorie, table.row_count

    nach_text, nach_severity, nach_kategorie, alle = asyncio.run(drive())

    assert nach_text == 2
    assert nach_severity == 3
    assert nach_kategorie == 2
    assert alle == 6


def test_app_ueberlebt_kaputten_report(tmp_path: Path) -> None:
    report = tmp_path / "kaputt.xml"
    report.write_text("<Report><Issues>", encoding="utf-8")

    async def drive() -> int:
        app = InspectCodeApp(xml_path=str(report))
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            return app.query_one("#findings-data", DataTable).row_count

    assert asyncio.run(drive()) == 0
