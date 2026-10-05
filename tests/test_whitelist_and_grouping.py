"""Whitelist, Top-10-Gruppierung und Dauerformat.

Die Whitelist blendet bekannte Findings aus (type_id exakt, message als
Teilmuster mit Wildcards). Die Top-10-Ansicht gruppiert nach Typ, Kategorie
und Datei und sortiert absteigend nach Haeufigkeit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from inspectcode_tui.app import InspectCodeApp, _format_duration
from inspectcode_tui.i18n import t
from inspectcode_tui.models.finding import Finding
from inspectcode_tui.screens.top_findings import TopFindingsScreen, _truncate


def _finding(type_id: str, message: str = "m", file: str = "A.cs", category: str = "Cat") -> Finding:
    """Baut ein Finding mit den fuer Whitelist und Gruppierung relevanten Feldern."""
    return Finding(
        type_id=type_id,
        file=file,
        line=1,
        offset="",
        message=message,
        severity="WARNING",
        category=category,
        category_id="",
        description="",
        project_name="",
    )


def _app_with_whitelist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rules: object, findings: list[Finding]
) -> InspectCodeApp:
    """App ohne Start, deren Whitelist auf eine Testdatei zeigt."""
    whitelist = tmp_path / "whitelist.json"
    whitelist.write_text(json.dumps({"rules": rules}) if not isinstance(rules, str) else rules, encoding="utf-8")
    monkeypatch.setattr(InspectCodeApp, "_find_whitelist", lambda self: whitelist)

    app = InspectCodeApp()
    app._findings = list(findings)
    return app


# ---------------------------------------------------------------------------
# Whitelist
# ---------------------------------------------------------------------------


def test_whitelist_type_id_entfernt_alle_dieses_typs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings = [_finding("InvalidXmlDocComment"), _finding("InvalidXmlDocComment"), _finding("UnusedVariable")]
    app = _app_with_whitelist(monkeypatch, tmp_path, [{"type_id": "InvalidXmlDocComment"}], findings)

    removed = app._apply_whitelist()

    assert removed == 2
    assert [f.type_id for f in app._findings] == ["UnusedVariable"]


def test_whitelist_type_id_ist_exakt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings = [_finding("UnusedVariable.Compiler"), _finding("unusedvariable")]
    app = _app_with_whitelist(monkeypatch, tmp_path, [{"type_id": "UnusedVariable"}], findings)

    assert app._apply_whitelist() == 0
    assert len(app._findings) == 2


def test_whitelist_typ_und_meldung_muessen_beide_passen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings = [
        _finding("InconsistentNaming", "Name '_logger' does not match rule"),
        _finding("InconsistentNaming", "Name 'Foo' does not match rule"),
        _finding("UnusedVariable", "Name '_logger' is never used"),
    ]
    rules = [{"type_id": "InconsistentNaming", "message": "'_*'"}]
    app = _app_with_whitelist(monkeypatch, tmp_path, rules, findings)

    assert app._apply_whitelist() == 1
    assert [f.message for f in app._findings] == [
        "Name 'Foo' does not match rule",
        "Name '_logger' is never used",
    ]


def test_whitelist_nur_meldung_gilt_fuer_alle_typen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings = [_finding("A", "Generated code ahead"), _finding("B", "in generated code"), _finding("C", "anders")]
    # Teilmuster: wird intern zu *...* erweitert
    app = _app_with_whitelist(monkeypatch, tmp_path, [{"message": "enerated code"}], findings)

    assert app._apply_whitelist() == 2
    assert [f.type_id for f in app._findings] == ["C"]


@pytest.mark.parametrize("content", ["{kaputt", json.dumps({"rules": []}), json.dumps({"andere": 1})])
def test_whitelist_kaputt_oder_leer_entfernt_nichts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str
) -> None:
    findings = [_finding("A"), _finding("B")]
    app = _app_with_whitelist(monkeypatch, tmp_path, content, findings)

    assert app._apply_whitelist() == 0
    assert len(app._findings) == 2


def test_whitelist_wird_im_arbeitsverzeichnis_gefunden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "whitelist.json").write_text("{}", encoding="utf-8")

    assert InspectCodeApp()._find_whitelist() == tmp_path / "whitelist.json"


# ---------------------------------------------------------------------------
# Top-10-Gruppierung
# ---------------------------------------------------------------------------


def _section(plain: str, start_marker: str, end_marker: str | None) -> list[str]:
    """Schneidet einen Abschnitt aus dem Chart-Text und liefert die Label-Zeilen."""
    start = plain.index(start_marker)
    end = plain.index(end_marker, start) if end_marker else len(plain)
    lines = plain[start:end].splitlines()
    return [line.strip() for line in lines if line.strip()[:1].isdigit()]


def test_top_findings_sortiert_absteigend_nach_haeufigkeit() -> None:
    findings = (
        [_finding("Selten", file="B.cs")]
        + [_finding("Haeufig", file="A.cs")] * 5
        + [_finding("Mittel", file="A.cs", category="Andere")] * 3
    )

    plain = TopFindingsScreen(findings)._build_chart().plain
    types = _section(plain, t("top.types"), t("top.categories"))

    assert types[0].startswith("1. Haeufig")
    assert types[1].startswith("2. Mittel")
    assert types[2].startswith("3. Selten")
    assert "5x" in plain and "3x" in plain


def test_top_findings_hoechstens_zehn_eintraege_je_gruppe() -> None:
    findings = [_finding(f"Typ{i:02d}") for i in range(15)]

    plain = TopFindingsScreen(findings)._build_chart().plain
    types = _section(plain, t("top.types"), t("top.categories"))

    assert len(types) == 10


def test_top_findings_leere_kategorie_bekommt_platzhalter() -> None:
    plain = TopFindingsScreen([_finding("A", category="")])._build_chart().plain
    categories = _section(plain, t("top.categories"), t("top.files"))

    assert categories == [f"1. {t('top.no_category')}"]


def test_lange_labels_werden_gekuerzt() -> None:
    assert _truncate("x" * 10, 10) == "x" * 10
    assert _truncate("x" * 11, 10) == "xxxxxxx..."
    assert len(_truncate("y" * 200, 80)) == 80


# ---------------------------------------------------------------------------
# Dauerformat im Untertitel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (0, "0.0s"),
        (12_340, "12.3s"),
        (60_000, "1m 0s"),
        (150_000, "2m 30s"),
        (3_599_000, "59m 59s"),
        (3_600_000, "1h 0m 0s"),
        (3_930_000, "1h 5m 30s"),
    ],
)
def test_dauerformat(ms: int, expected: str) -> None:
    assert _format_duration(ms) == expected
