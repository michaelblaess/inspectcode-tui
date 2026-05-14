"""Service fuer das Anwenden von Fixes auf Findings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..i18n import t
from ..models.finding import Finding


@dataclass
class FixResult:
    """Ergebnis eines Fix-Versuchs."""

    success: bool
    message: str
    old_content: str = ""
    new_content: str = ""
    backup_path: str = ""


class Fixer:
    """Wendet Fixes auf InspectCode Findings an."""

    # Mapping von TypeId zu Fix-Strategie
    FIXABLE_TYPES = {
        "RedundantUsingDirective",
        "UnusedVariable",
        "RedundantAssignment",
        "EmptyConstructor",
        "RedundantBaseConstructorCall",
        "RedundantDefaultMemberInitializer",
        "PossibleIntendedRethrow",
        "RedundantBaseQualifier",
        "HeuristicUnreachableCode",
        "ConstantConditionalAccessQualifier",
        "StringIndexOfIsCultureSpecific.1",
    }

    def __init__(self, solution_dir: str | Path) -> None:
        self.solution_dir = Path(solution_dir)

    def can_fix(self, finding: Finding) -> bool:
        """Prueft ob ein Finding automatisch gefixt werden kann."""
        return finding.type_id in self.FIXABLE_TYPES

    def preview_fix(self, finding: Finding) -> FixResult:
        """Zeigt eine Vorschau des Fixes an, ohne ihn anzuwenden."""
        file_path = self._resolve_path(finding.file)
        if not file_path.exists():
            return FixResult(False, t("fixer.file_not_found", path=file_path))

        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except OSError as e:
            return FixResult(False, t("fixer.read_error", error=e))

        new_content = self._apply_fix_to_content(finding, content)
        if new_content == content:
            return FixResult(False, t("fixer.no_change"))

        return FixResult(
            success=True,
            message=t("fixer.preview", type_id=finding.type_id),
            old_content=content,
            new_content=new_content,
        )

    def apply_fix(self, finding: Finding) -> FixResult:
        """Wendet einen Fix an (Datei direkt aendern, Git ist das Sicherheitsnetz).

        Args:
            finding: Das zu fixende Finding.

        Returns:
            FixResult mit Erfolgs-Status und Details.
        """
        file_path = self._resolve_path(finding.file)
        if not file_path.exists():
            return FixResult(False, t("fixer.file_not_found", path=file_path))

        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except OSError as e:
            return FixResult(False, t("fixer.read_error", error=e))

        new_content = self._apply_fix_to_content(finding, content)
        if new_content == content:
            return FixResult(False, t("fixer.no_change"))

        # Fix anwenden
        try:
            file_path.write_text(new_content, encoding="utf-8")
        except OSError as e:
            return FixResult(False, t("fixer.write_error", error=e))

        return FixResult(
            success=True,
            message=t("fixer.applied", type_id=finding.type_id, file=finding.filename, line=finding.line),
            old_content=content,
            new_content=new_content,
        )

    def _resolve_path(self, relative_path: str) -> Path:
        """Loest einen relativen Pfad aus dem Report auf."""
        # InspectCode gibt Pfade relativ zur Solution an
        normalized = relative_path.replace("\\", "/")
        return self.solution_dir / normalized

    def _apply_fix_to_content(self, finding: Finding, content: str) -> str:
        """Wendet den Fix auf den Datei-Inhalt an."""
        lines = content.splitlines(keepends=True)
        line_idx = finding.line - 1  # 0-basierter Index

        if line_idx < 0 or line_idx >= len(lines):
            return content

        fix_method = self._get_fix_method(finding.type_id)
        if fix_method is None:
            return content

        return fix_method(finding, lines, line_idx)

    def _get_fix_method(self, type_id: str):
        """Gibt die Fix-Methode fuer einen TypeId zurueck."""
        methods = {
            "RedundantUsingDirective": self._fix_remove_line,
            "UnusedVariable": self._fix_remove_line,
            "RedundantAssignment": self._fix_remove_line,
            "EmptyConstructor": self._fix_empty_constructor,
            "RedundantBaseConstructorCall": self._fix_redundant_base_call,
            "RedundantDefaultMemberInitializer": self._fix_redundant_default_initializer,
            "PossibleIntendedRethrow": self._fix_possible_intended_rethrow,
            "RedundantBaseQualifier": self._fix_redundant_base_qualifier,
            "HeuristicUnreachableCode": self._fix_remove_line,
            "ConstantConditionalAccessQualifier": self._fix_constant_conditional_access,
            "StringIndexOfIsCultureSpecific.1": self._fix_string_indexof_culture,
        }
        return methods.get(type_id)

    def _fix_remove_line(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Entfernt eine Zeile komplett."""
        lines[line_idx] = ""
        return "".join(lines)

    def _fix_empty_constructor(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Entfernt einen leeren Konstruktor (mehrzeilig)."""
        # Finde den Anfang und das Ende des Konstruktors
        start = line_idx
        brace_count = 0
        end = start

        for i in range(start, len(lines)):
            for ch in lines[i]:
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
            if brace_count > 0 and i > start:
                continue
            if brace_count == 0 and i > start:
                end = i
                break

        if end <= start:
            # Fallback: nur Zeile entfernen
            end = start

        for i in range(start, end + 1):
            lines[i] = ""

        return "".join(lines)

    def _fix_redundant_base_call(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Entfernt redundanten base()-Aufruf."""
        line = lines[line_idx]
        # Muster: `: base()` entfernen
        new_line = re.sub(r"\s*:\s*base\(\)", "", line)
        lines[line_idx] = new_line
        return "".join(lines)

    def _fix_possible_intended_rethrow(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Ersetzt 'throw ex;' durch 'throw;' um Stacktrace zu erhalten.

        Beispiel:
            catch (Exception ex) { throw ex; }  ->  catch (Exception ex) { throw; }
        """
        line = lines[line_idx]
        # Muster: throw <variablenname>;
        new_line = re.sub(r"\bthrow\s+\w+\s*;", "throw;", line)
        lines[line_idx] = new_line
        return "".join(lines)

    def _fix_redundant_base_qualifier(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Entfernt redundanten base.-Qualifier bei Methodenaufrufen.

        Beispiel:
            base.OnPreRender(e);  ->  OnPreRender(e);
            base.ToString()       ->  ToString()
        """
        line = lines[line_idx]
        new_line = re.sub(r"\bbase\.", "", line)
        lines[line_idx] = new_line
        return "".join(lines)

    def _fix_constant_conditional_access(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Ersetzt '?.' durch '.' wenn das Objekt nie null sein kann.

        Beispiel:
            myList?.Count   ->  myList.Count
            this?.Method()  ->  this.Method()
        """
        line = lines[line_idx]
        # Alle ?. auf der Zeile durch . ersetzen
        new_line = line.replace("?.", ".")
        lines[line_idx] = new_line
        return "".join(lines)

    def _fix_string_indexof_culture(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Fuegt StringComparison.Ordinal zu IndexOf/LastIndexOf hinzu.

        Beispiele:
            str.IndexOf("x")            ->  str.IndexOf("x", StringComparison.Ordinal)
            str.LastIndexOf("x")        ->  str.LastIndexOf("x", StringComparison.Ordinal)
            str.IndexOf(value)           ->  str.IndexOf(value, StringComparison.Ordinal)
        """
        line = lines[line_idx]
        # Muster: .IndexOf(<args>) oder .LastIndexOf(<args>) ohne StringComparison
        # Nur einfache Faelle: ein Argument in Klammern
        new_line = re.sub(
            r"\.(IndexOf|LastIndexOf)\(([^,)]+)\)",
            r".\1(\2, StringComparison.Ordinal)",
            line,
        )
        lines[line_idx] = new_line
        return "".join(lines)

    def _fix_redundant_default_initializer(self, finding: Finding, lines: list[str], line_idx: int) -> str:
        """Entfernt redundante Default-Initialisierungen bei Feldern.

        Beispiele:
            private int count = 0;       -> private int count;
            private string name = null;  -> private string name;
            private bool flag = false;   -> private bool flag;
            private double val = 0.0;    -> private double val;
            private object obj = default; -> private object obj;
        """
        line = lines[line_idx]
        # Pattern: "= <default-wert>" vor dem Semikolon entfernen
        # Erfasst: 0, 0L, 0f, 0d, 0.0, 0.0f, 0.0d, null, false, default,
        #          default(T), '\0', new Nullable<T>() etc.
        new_line = re.sub(
            r"\s*=\s*(?:0(?:\.\d+)?[fdlumFDLUM]*|null|false|default(?:\([^)]*\))?)\s*(?=;)",
            "",
            line,
        )
        lines[line_idx] = new_line
        return "".join(lines)
