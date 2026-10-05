"""Einlesen der InspectCode-Reports (klassisches XML und SARIF/JSON).

Der Parser erkennt das Format am ersten Zeichen und fuehrt die Angaben aus
den Regel-Definitionen (IssueType bzw. SARIF-Rule) mit den einzelnen Treffern
zusammen. Genau diese Zusammenfuehrung wird hier festgehalten.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inspectcode_tui.models.report import Report


def _by_line(findings: list, line: int):
    """Liefert das eine Finding auf der angegebenen Zeile."""
    matches = [f for f in findings if f.line == line]
    assert len(matches) == 1, f"Erwartet genau ein Finding auf Zeile {line}, gefunden: {matches}"
    return matches[0]


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------


def test_xml_kopfdaten_und_anzahl(fixtures_dir: Path) -> None:
    report = Report(fixtures_dir / "report.xml")
    findings = report.parse()

    assert report.solution_name == "Demo.sln"
    assert report.tools_version == "2024.3.5"
    assert len(findings) == 6
    assert findings is report.findings


def test_xml_finding_uebernimmt_angaben_aus_issuetype(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.xml").parse()
    finding = _by_line(findings, 12)

    assert finding.type_id == "CSharpErrors"
    assert finding.severity == "ERROR"
    assert finding.category == "C# Compiler Errors"
    assert finding.category_id == "CompilerErrors"
    assert finding.description == "C# Compiler Errors"
    assert finding.file == "Demo.Core\\Models\\Order.cs"
    assert finding.filename == "Order.cs"
    assert finding.offset == "120-131"
    assert finding.message == "Cannot resolve symbol 'Customer'"
    assert finding.project_name == "Demo.Core"


def test_xml_projektname_je_project_knoten(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.xml").parse()
    projects = {f.project_name for f in findings}

    assert projects == {"Demo.Core", "Demo.Web"}
    assert _by_line(findings, 7).project_name == "Demo.Web"


def test_xml_wiki_url_aus_issuetype(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.xml").parse()

    assert _by_line(findings, 1).wiki_url == "https://www.jetbrains.com/help/resharper/RedundantUsingDirective.html"
    # IssueType ohne WikiUrl -> leer, nicht None
    assert _by_line(findings, 20).wiki_url == ""


def test_xml_unbekannter_typ_und_kaputte_zeilennummer(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.xml").parse()
    finding = next(f for f in findings if f.type_id == "UnknownInspection")

    # Line="abc" darf den Import nicht abbrechen
    assert finding.line == 0
    # Ohne IssueType faellt die Severity auf WARNING zurueck
    assert finding.severity == "WARNING"
    assert finding.category == ""


def test_xml_ohne_issues_liefert_leere_liste(tmp_path: Path) -> None:
    path = tmp_path / "leer.xml"
    path.write_text('<Report ToolsVersion="1.0"><Information><Solution>X.sln</Solution></Information></Report>')

    report = Report(path)
    assert report.parse() == []
    assert report.solution_name == "X.sln"


# ---------------------------------------------------------------------------
# SARIF
# ---------------------------------------------------------------------------


def test_sarif_kopfdaten_und_anzahl(fixtures_dir: Path) -> None:
    report = Report(fixtures_dir / "report.sarif.json")
    findings = report.parse()

    assert len(findings) == 3
    assert report.tools_version == "2025.2.0"
    # properties.solutionName hat Vorrang vor dem Treibernamen
    assert report.solution_name == "Demo.sln"


def test_sarif_severity_aus_regel_default(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()

    assert _by_line(findings, 3).severity == "WARNING"
    assert _by_line(findings, 12).severity == "ERROR"


def test_sarif_result_level_ueberschreibt_regel(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()

    # Regel sagt 'note' (SUGGESTION), das Ergebnis selbst 'error'
    assert _by_line(findings, 20).severity == "ERROR"


def test_sarif_pfad_offset_und_kategorie(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()
    finding = _by_line(findings, 3)

    # SARIF-URIs mit '/' werden auf Windows-Trenner umgestellt
    assert finding.file == "Demo.Core\\Services\\OrderService.cs"
    assert finding.offset == "40-55"
    assert finding.category == "CodeRedundancy"
    assert finding.category_id == "Redundancies in Code"
    assert finding.description == "Redundant using directive"
    assert finding.wiki_url == "https://www.jetbrains.com/help/resharper/RedundantUsingDirective.html"


def test_sarif_offset_aus_startcolumn(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()

    assert _by_line(findings, 12).offset == "9"
    # Weder charOffset noch startColumn -> leer
    assert _by_line(findings, 20).offset == ""


def test_sarif_projektname_aus_logical_locations(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()

    # kind=module gewinnt, auch wenn es nicht an erster Stelle steht
    assert _by_line(findings, 3).project_name == "Demo.Core"
    # ohne module-Eintrag: erster logischer Ort
    assert _by_line(findings, 20).project_name == "Demo.Web"


def test_sarif_regel_ueber_id_ohne_rule_index(fixtures_dir: Path) -> None:
    findings = Report(fixtures_dir / "report.sarif.json").parse()
    finding = _by_line(findings, 20)

    # Kein ruleIndex im Ergebnis -> Nachschlagen ueber ruleId
    assert finding.type_id == "ConvertToAutoProperty"
    assert finding.description == "Convert property into auto-property"


def test_sarif_ohne_runs_wirft_fehler(tmp_path: Path) -> None:
    path = tmp_path / "leer.sarif"
    path.write_text('{"version": "2.1.0", "runs": []}')

    with pytest.raises(ValueError):
        Report(path).parse()


# ---------------------------------------------------------------------------
# Formaterkennung
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "expected"), [("report.xml", 6), ("report.sarif.json", 3)])
def test_formaterkennung_mit_bom(fixtures_dir: Path, tmp_path: Path, name: str, expected: int) -> None:
    # Unter Windows steht gern ein UTF-8-BOM am Dateianfang
    path = tmp_path / name
    path.write_bytes(b"\xef\xbb\xbf" + (fixtures_dir / name).read_bytes())

    assert len(Report(path).parse()) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        # XML-Deklaration muss laut Spezifikation am Anfang stehen, deshalb hier ohne
        (b'\r\n  \t<Report><Issues><Project Name="P"><Issue TypeId="X" Line="1" /></Project></Issues></Report>', 1),
        (b'\r\n  \t{"runs": [{"results": [{"ruleId": "X"}]}]}', 1),
    ],
)
def test_formaterkennung_ueberspringt_fuehrenden_leerraum(tmp_path: Path, content: bytes, expected: int) -> None:
    path = tmp_path / "report"
    path.write_bytes(content)

    assert len(Report(path).parse()) == expected


@pytest.mark.parametrize("content", [b"", b"Kein Report", b"   \n"])
def test_unbekanntes_format_wirft_fehler(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "kaputt.txt"
    path.write_bytes(content)

    with pytest.raises(ValueError):
        Report(path).parse()
