"""Filter und Zaehlungen auf dem Report.

``filter_by_severity`` steuert, was beim Start ueberhaupt in der Tabelle
landet, ``filter_by_files`` den Git-Commit-Modus. Beide entscheiden also
darueber, ob ein Finding fuer den Anwender sichtbar ist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inspectcode_tui.models.finding import Finding
from inspectcode_tui.models.report import Report


def _finding(file: str = "A.cs", severity: str = "WARNING", category: str = "Cat", type_id: str = "T") -> Finding:
    """Baut ein Finding mit den fuer Filter relevanten Feldern."""
    return Finding(
        type_id=type_id,
        file=file,
        line=1,
        offset="",
        message="m",
        severity=severity,
        category=category,
        category_id="",
        description="",
        project_name="",
    )


def _report(findings: list[Finding]) -> Report:
    """Report ohne Datei, nur mit vorgegebenen Findings."""
    report = Report("unbenutzt.xml")
    report.findings = findings
    return report


@pytest.fixture
def xml_report(fixtures_dir: Path) -> Report:
    """Geparster XML-Beispielreport mit je einem Finding pro Severity und mehr."""
    report = Report(fixtures_dir / "report.xml")
    report.parse()
    return report


# ---------------------------------------------------------------------------
# filter_by_severity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("minimum", "expected"),
    [
        ("HINT", {"ERROR", "WARNING", "SUGGESTION", "HINT"}),
        ("SUGGESTION", {"ERROR", "WARNING", "SUGGESTION"}),
        ("WARNING", {"ERROR", "WARNING"}),
        ("ERROR", {"ERROR"}),
    ],
)
def test_severity_filter_laesst_nur_ab_minimum_durch(xml_report: Report, minimum: str, expected: set[str]) -> None:
    result = xml_report.filter_by_severity(minimum)

    assert {f.severity for f in result} == expected


def test_severity_filter_zaehlt_korrekt(xml_report: Report) -> None:
    # 3x WARNING (2 Usings + unbekannter Typ mit Fallback) + 1x ERROR
    assert len(xml_report.filter_by_severity("WARNING")) == 4
    assert len(xml_report.filter_by_severity("HINT")) == 6


def test_severity_filter_ignoriert_gross_kleinschreibung() -> None:
    report = _report([_finding(severity="error"), _finding(severity="hint")])

    assert len(report.filter_by_severity("error")) == 1
    assert len(report.filter_by_severity("Hint")) == 2


def test_severity_filter_unbekanntes_minimum_wirkt_wie_warning() -> None:
    report = _report([_finding(severity=s) for s in ("ERROR", "WARNING", "SUGGESTION", "HINT")])

    assert {f.severity for f in report.filter_by_severity("QUATSCH")} == {"ERROR", "WARNING"}


def test_severity_filter_unbekannte_severity_gilt_als_niedrigste() -> None:
    report = _report([_finding(severity="INFO")])

    assert report.filter_by_severity("HINT") != []
    assert report.filter_by_severity("SUGGESTION") == []


# ---------------------------------------------------------------------------
# filter_by_files (Git-Commit-Modus)
# ---------------------------------------------------------------------------


def test_dateifilter_ohne_dateien_liefert_kopie_aller_findings() -> None:
    findings = [_finding("A.cs"), _finding("B.cs")]
    report = _report(findings)

    result = report.filter_by_files([])

    assert result == findings
    assert result is not report.findings


def test_dateifilter_gleicht_trenner_und_schreibweise_an() -> None:
    report = _report(
        [
            _finding("Demo.Core\\Services\\OrderService.cs"),
            _finding("Demo.Core\\Models\\Order.cs"),
            _finding("Demo.Web\\Startup.cs"),
        ]
    )

    # git liefert '/' und evtl. andere Schreibweise, InspectCode '\'
    result = report.filter_by_files(["demo.core/services/orderservice.cs", "Demo.Web/Startup.cs"])

    assert [f.filename for f in result] == ["OrderService.cs", "Startup.cs"]


def test_dateifilter_repo_relativ_gegen_solution_relativ() -> None:
    # Solution liegt in src/, git-Pfade sind relativ zum Repo-Root
    report = _report([_finding("Demo.Core\\Models\\Order.cs"), _finding("Demo.Core\\Models\\Customer.cs")])

    result = report.filter_by_files(["src/Demo.Core/Models/Order.cs"])

    assert [f.filename for f in result] == ["Order.cs"]


def test_dateifilter_absolute_reportpfade() -> None:
    report = _report([_finding("C:\\Work\\Demo\\Demo.Core\\Models\\Order.cs")])

    assert len(report.filter_by_files(["Demo.Core/Models/Order.cs"])) == 1
    assert report.filter_by_files(["Demo.Core/Models/Other.cs"]) == []


def test_dateifilter_finding_nur_einmal_trotz_mehrerer_treffer() -> None:
    report = _report([_finding("Demo\\Order.cs")])

    assert len(report.filter_by_files(["Demo/Order.cs", "Order.cs", "src/Demo/Order.cs"])) == 1


@pytest.mark.xfail(
    strict=True,
    reason="Bekannter Fehler: endswith ohne Pfadgrenze - 'Foo.cs' passt auf 'src/MyFoo.cs'",
)
def test_dateifilter_beachtet_pfadgrenzen() -> None:
    report = _report([_finding("Foo.cs")])

    assert report.filter_by_files(["src/MyFoo.cs"]) == []


# ---------------------------------------------------------------------------
# Zaehlungen
# ---------------------------------------------------------------------------


def test_severity_zaehlung(xml_report: Report) -> None:
    assert xml_report.get_severity_counts() == {"WARNING": 3, "ERROR": 1, "SUGGESTION": 1, "HINT": 1}


def test_severity_zaehlung_normalisiert_schreibweise() -> None:
    report = _report([_finding(severity="error"), _finding(severity="ERROR")])

    assert report.get_severity_counts() == {"ERROR": 2}


def test_kategorie_zaehlung(xml_report: Report) -> None:
    counts = xml_report.get_category_counts()

    assert counts["Redundancies in Code"] == 2
    assert counts["C# Compiler Errors"] == 1
    # Finding ohne IssueType landet unter leerer Kategorie
    assert counts[""] == 1
    assert sum(counts.values()) == 6
