"""Parser fuer InspectCode Report-Dateien (XML und SARIF/JSON)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .finding import Finding


class Report:
    """Parst und haelt InspectCode Report-Daten (XML oder SARIF/JSON)."""

    def __init__(self, report_path: str | Path) -> None:
        self.report_path = Path(report_path)
        self.solution_name: str = ""
        self.tools_version: str = ""
        self.findings: list[Finding] = []
        self._issue_types: dict[str, dict[str, str]] = {}

    def parse(self) -> list[Finding]:
        """Parst die Report-Datei (erkennt Format automatisch)."""
        raw = self.report_path.read_bytes()

        # Format erkennen: JSON beginnt mit '{', XML mit '<'
        first_char = ""
        for byte in raw:
            ch = chr(byte)
            if ch in (" ", "\t", "\n", "\r", "\xef", "\xbb", "\xbf"):
                # Whitespace und BOM ueberspringen
                continue
            first_char = ch
            break

        if first_char == "{":
            self._parse_sarif(raw)
        elif first_char == "<":
            self._parse_xml(raw)
        else:
            raise ValueError(
                f"Unbekanntes Report-Format (erstes Zeichen: '{first_char}'). "
                "Erwartet wird XML oder SARIF/JSON."
            )

        return self.findings

    # ------------------------------------------------------------------
    # XML-Parser (klassisches InspectCode-Format)
    # ------------------------------------------------------------------

    def _parse_xml(self, raw: bytes) -> None:
        """Parst eine InspectCode XML-Report-Datei."""
        root = ET.fromstring(raw)

        self.tools_version = root.get("ToolsVersion", "")

        info = root.find("Information")
        if info is not None:
            sol = info.find("Solution")
            if sol is not None and sol.text:
                self.solution_name = sol.text

        self._parse_xml_issue_types(root)
        self._parse_xml_issues(root)

    def _parse_xml_issue_types(self, root: ET.Element) -> None:
        """Parst die IssueType-Definitionen aus XML."""
        issue_types_elem = root.find("IssueTypes")
        if issue_types_elem is None:
            return

        for it in issue_types_elem.findall("IssueType"):
            type_id = it.get("Id", "")
            self._issue_types[type_id] = {
                "category": it.get("Category", ""),
                "category_id": it.get("CategoryId", ""),
                "description": it.get("Description", ""),
                "severity": it.get("Severity", "WARNING"),
                "wiki_url": it.get("WikiUrl", ""),
            }

    def _parse_xml_issues(self, root: ET.Element) -> None:
        """Parst die einzelnen Issues aus XML."""
        issues_elem = root.find("Issues")
        if issues_elem is None:
            return

        for project in issues_elem.findall("Project"):
            project_name = project.get("Name", "")

            for issue in project.findall("Issue"):
                type_id = issue.get("TypeId", "")
                issue_type = self._issue_types.get(type_id, {})

                line_str = issue.get("Line", "0")
                try:
                    line = int(line_str)
                except ValueError:
                    line = 0

                finding = Finding(
                    type_id=type_id,
                    file=issue.get("File", ""),
                    line=line,
                    offset=issue.get("Offset", ""),
                    message=issue.get("Message", ""),
                    severity=issue_type.get("severity", "WARNING"),
                    category=issue_type.get("category", ""),
                    category_id=issue_type.get("category_id", ""),
                    description=issue_type.get("description", ""),
                    project_name=project_name,
                    wiki_url=issue_type.get("wiki_url", ""),
                )
                self.findings.append(finding)

    # ------------------------------------------------------------------
    # SARIF/JSON-Parser (neues InspectCode-Format ab 2025.x)
    # ------------------------------------------------------------------

    # SARIF 'level' -> unsere Severity-Namen
    _SARIF_LEVEL_MAP: dict[str, str] = {
        "error": "ERROR",
        "warning": "WARNING",
        "note": "SUGGESTION",
        "none": "HINT",
    }

    def _parse_sarif(self, raw: bytes) -> None:
        """Parst eine SARIF/JSON-Report-Datei."""
        data = json.loads(raw)

        runs = data.get("runs", [])
        if not runs:
            raise ValueError("SARIF-Datei enthaelt keine 'runs'.")

        run = runs[0]

        # Tool-Info
        tool = run.get("tool", {})
        driver = tool.get("driver", {})
        self.tools_version = driver.get("version", "")
        self.solution_name = driver.get("name", "InspectCode")

        # Regeln (IssueTypes) aufbauen
        rules = driver.get("rules", [])
        rules_by_index: dict[int, dict[str, str]] = {}
        for idx, rule in enumerate(rules):
            rule_id = rule.get("id", "")
            default_cfg = rule.get("defaultConfiguration", {})
            level = default_cfg.get("level", "warning")

            # Kategorie aus relationships extrahieren
            category = ""
            category_id = ""
            relationships = rule.get("relationships", [])
            for rel in relationships:
                target = rel.get("target", {})
                if target:
                    category = target.get("id", "")
                    tool_component = target.get("toolComponent", {})
                    if tool_component:
                        category_id = tool_component.get("name", "")
                    break

            rule_info = {
                "category": category,
                "category_id": category_id,
                "description": _sarif_text(rule.get("shortDescription")),
                "severity": self._SARIF_LEVEL_MAP.get(level, "WARNING"),
                "wiki_url": rule.get("helpUri", ""),
            }

            self._issue_types[rule_id] = rule_info
            rules_by_index[idx] = rule_info

        # Solution-Name aus properties extrahieren (falls vorhanden)
        properties = run.get("properties", {})
        if "solutionName" in properties:
            self.solution_name = properties["solutionName"]

        # Ergebnisse parsen
        results = run.get("results", [])
        for result in results:
            rule_id = result.get("ruleId", "")
            rule_index = result.get("ruleIndex")

            # Regel-Info nachschlagen (per Index oder ID)
            if rule_index is not None and rule_index in rules_by_index:
                rule_info = rules_by_index[rule_index]
            else:
                rule_info = self._issue_types.get(rule_id, {})

            # Severity: result.level ueberschreibt rule default
            level = result.get("level", "")
            if level:
                severity = self._SARIF_LEVEL_MAP.get(level, "WARNING")
            else:
                severity = rule_info.get("severity", "WARNING")

            # Message
            message = _sarif_text(result.get("message"))

            # Location
            file_path = ""
            line = 0
            offset = ""
            locations = result.get("locations", [])
            if locations:
                phys = locations[0].get("physicalLocation", {})
                artifact = phys.get("artifactLocation", {})
                uri = artifact.get("uri", "")
                # SARIF URIs nutzen '/' als Trennzeichen
                file_path = uri.replace("/", "\\")

                region = phys.get("region", {})
                line = region.get("startLine", 0)

                # Offset aus charOffset/charLength oder startColumn
                char_offset = region.get("charOffset")
                char_length = region.get("charLength")
                if char_offset is not None and char_length is not None:
                    offset = f"{char_offset}-{char_offset + char_length}"
                elif region.get("startColumn"):
                    offset = str(region["startColumn"])

            # Projekt-Name aus logicalLocations extrahieren
            project_name = ""
            logical = result.get("logicalLocations", [])
            if logical:
                for loc in logical:
                    if loc.get("kind") == "module":
                        project_name = loc.get("name", "")
                        break
                if not project_name and logical:
                    project_name = logical[0].get("name", "")

            finding = Finding(
                type_id=rule_id,
                file=file_path,
                line=line,
                offset=offset,
                message=message,
                severity=severity,
                category=rule_info.get("category", ""),
                category_id=rule_info.get("category_id", ""),
                description=rule_info.get("description", ""),
                project_name=project_name,
                wiki_url=rule_info.get("wiki_url", ""),
            )
            self.findings.append(finding)

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    def get_severity_counts(self) -> dict[str, int]:
        """Zaehlt Findings nach Severity."""
        counts: dict[str, int] = {}
        for f in self.findings:
            sev = f.severity.upper()
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def get_category_counts(self) -> dict[str, int]:
        """Zaehlt Findings nach Kategorie."""
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts

    def filter_by_files(self, files: list[str]) -> list[Finding]:
        """Filtert Findings auf bestimmte Dateien (fuer Git-Commit-Modus).

        Vergleicht case-insensitiv und prueft ob der Dateipfad des Findings
        mit einem der angegebenen Pfade endet (um relative vs. absolute
        Pfade abzugleichen).

        Args:
            files: Liste der Dateipfade (relativ zum Repo-Root).

        Returns:
            Gefilterte Liste der Findings.
        """
        if not files:
            return list(self.findings)

        # Normalisierung: Backslash -> Forward-Slash, lowercase
        normalized = {f.replace("\\", "/").lower() for f in files}

        result = []
        for finding in self.findings:
            finding_path = finding.file.replace("\\", "/").lower()
            for file_path in normalized:
                if finding_path.endswith(file_path) or file_path.endswith(finding_path):
                    result.append(finding)
                    break

        return result

    def filter_by_severity(self, min_severity: str) -> list[Finding]:
        """Filtert Findings nach minimaler Severity."""
        severity_order = {"HINT": 0, "SUGGESTION": 1, "WARNING": 2, "ERROR": 3}
        min_level = severity_order.get(min_severity.upper(), 2)
        return [
            f for f in self.findings
            if severity_order.get(f.severity.upper(), 0) >= min_level
        ]


def _sarif_text(msg_obj: dict | None) -> str:
    """Extrahiert den Text aus einem SARIF message/description-Objekt."""
    if not msg_obj:
        return ""
    if isinstance(msg_obj, dict):
        return msg_obj.get("text", "")
    return str(msg_obj)
