#!/usr/bin/env python3
"""Reject fictional-data experiments and results in manuscript artifacts.

This check is intentionally separate from ``check_project_readiness.py``.  The
readiness checker has a metadata-only contract; this script audits publication
artifacts and the code paths that can regenerate them.

The audit covers the active LaTeX dependency closure rooted at
``overleaf/main.tex``, textual members of Overleaf export ZIPs, the canonical
manuscript PDF and any misplaced rendered copies when ``pdftotext`` is
available, and active scripts that can write fictional/synthetic/demo results
into ``overleaf``.  Records below ``Storage`` and literature databases are
deliberately outside its scope.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterable


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]

TEXTUAL_EXPORT_SUFFIXES = {
    ".csv",
    ".json",
    ".md",
    ".py",
    ".svg",
    ".tex",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
SCRIPT_SUFFIXES = {".js", ".mjs", ".py", ".sh", ".ts"}
SCRIPT_SCAN_IGNORED_TOP_LEVEL = {
    ".git",
    ".pnpm-store",
    "Storage",
    "node_modules",
    "output",
    "outputs",
    "overleaf",
    "paper",
    "review",
    "tmp",
}
SCRIPT_SCAN_IGNORED_DIRECTORY_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    "raw",
}

DATA_CLASS_RE = re.compile(r"\b(?:fictional|synthetic|demo(?:nstration)?)\b", re.I)
DATA_OR_RESULT_RE = re.compile(
    r"\b(?:"
    r"data(?:set)?s?|packets?|fixtures?|templates?|benchmarks?|"
    r"experiments?|qualifications?|pilots?|results?|measurements?|metrics?|"
    r"scores?|ratings?|rankings?|outputs?|evaluations?|performance|"
    r"accuracy|adequacy|coverage|tables?|figures?|model selection"
    r")\b",
    re.I,
)
INTERNAL_CONTEXT_RE = re.compile(
    r"(?:"
    r"\b(?:we|our|ours)\b|"
    r"\b(?:this|current|present)\s+"
    r"(?:paper|manuscript|study|project|work|section|experiment|qualification|pilot)\b|"
    r"\bthe\s+(?:completed\s+)?(?:qualification|pilot|experiment)\b|"
    r"\b(?:main|active)\s+(?:paper|manuscript)\b|"
    r"\bWarrantRoute\b|"
    r"\b(?:Table|Figure)\s+\d+\b|"
    r"\\(?:sub)*section\b|\\caption\b|\\label\b|\\(?:input|include)\b"
    r")",
    re.I,
)
EXCLUSION_RE = re.compile(
    r"(?:"
    r"\b(?:excluded|omitted|removed|prohibited|forbidden)\b|"
    r"\bno\s+(?:fictional|synthetic|demo(?:nstration)?)\b|"
    r"\b(?:fictional|synthetic|demo(?:nstration)?)\b.{0,60}"
    r"\b(?:not|never)\s+(?:included|used|reported|eligible|incorporated)\b|"
    r"\bnot\s+(?:included|used|reported|eligible|incorporated)\b.{0,60}"
    r"\b(?:fictional|synthetic|demo(?:nstration)?)\b"
    r")",
    re.I,
)
PROVENANCE_RE = re.compile(
    r"\b(?:data[_ -]?origin|data[_ -]?class|dataset[_ -]?type|"
    r"provenance[_ -]?class)\b\s*[:=]\s*[\"']?"
    r"(?:fictional|synthetic|demo(?:nstration)?)\b",
    re.I,
)
DIRECT_TEX_TOKEN_RE = re.compile(
    r"\\(?:input|include|label|ref|autoref)\s*\{[^}\n]*"
    r"(?:fictional|synthetic|demo)[^}\n]*\}",
    re.I,
)
FORBIDDEN_PATH_RE = re.compile(
    r"(?:"
    r"(?:fictional|synthetic|demo).{0,48}"
    r"(?:data|dataset|packet|fixture|benchmark|experiment|qualification|pilot|"
    r"result|metric|table|output)|"
    r"(?:data|dataset|packet|fixture|benchmark|experiment|qualification|pilot|"
    r"result|metric|table|output).{0,48}(?:fictional|synthetic|demo)"
    r")",
    re.I,
)

INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^}]+)\}")
OVERLEAF_DESTINATION_RE = re.compile(
    r"(?:[\"']overleaf[\"']|\boverleaf[/\\])", re.I
)
SCRIPT_WRITER_RE = re.compile(
    r"(?:write_text|write_bytes|writeFile(?:Sync)?|to_csv|to_json|savefig|"
    r"writestr|copyfile|shutil\.copy|\.write\s*\(|open\s*\([^\n]{0,160},\s*[\"'][wa])",
    re.I,
)


def _strip_tex_comments(text: str) -> str:
    """Remove unescaped TeX comments while preserving line numbers."""

    cleaned: list[str] = []
    for line in text.splitlines(keepends=True):
        cut = len(line)
        for index, character in enumerate(line):
            if character != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut = index
                break
        suffix = "\n" if line.endswith("\n") else ""
        cleaned.append(line[:cut].rstrip("\n") + suffix)
    return "".join(cleaned)


def _segments(text: str) -> Iterable[tuple[int, str]]:
    """Yield sentence/paragraph-sized text segments with one-based line numbers."""

    cursor = 0
    boundary = re.compile(r"[.!?](?=\s|$)|\n\s*\n|\Z", re.M)
    for match in boundary.finditer(text):
        end = match.end()
        segment = text[cursor:end]
        if segment.strip():
            line = text.count("\n", 0, cursor) + 1
            yield line, re.sub(r"\s+", " ", segment).strip()
        cursor = end


def _shorten(value: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


def scan_text(label: str, text: str, *, tex: bool = False) -> list[str]:
    """Return policy violations found in one manuscript-facing text artifact."""

    violations: list[str] = []

    provenance = PROVENANCE_RE.search(text)
    if provenance:
        line = text.count("\n", 0, provenance.start()) + 1
        violations.append(
            f"{label}:{line}: forbidden fictional-data provenance declaration"
        )

    token = DIRECT_TEX_TOKEN_RE.search(text)
    if token:
        line = text.count("\n", 0, token.start()) + 1
        violations.append(
            f"{label}:{line}: forbidden fictional-result TeX dependency/reference: "
            f"{_shorten(token.group(0))}"
        )

    searchable = _strip_tex_comments(text) if tex else text
    for line, segment in _segments(searchable):
        if not DATA_CLASS_RE.search(segment):
            continue
        if not DATA_OR_RESULT_RE.search(segment):
            continue
        if not INTERNAL_CONTEXT_RE.search(segment):
            continue
        if EXCLUSION_RE.search(segment):
            continue
        violations.append(
            f"{label}:{line}: internal fictional/synthetic/demo experiment or result: "
            f"{_shorten(segment)}"
        )
    return violations


def _forbidden_path(label: str, value: str) -> list[str]:
    if FORBIDDEN_PATH_RE.search(value.replace("\\", "/")):
        return [f"{label}: forbidden fictional-result path: {value}"]
    return []


def _resolve_dependency(
    manuscript_root: Path,
    source: Path,
    raw_name: str,
    suffixes: tuple[str, ...],
) -> Path | None:
    raw_path = Path(raw_name.strip())
    if raw_path.is_absolute():
        return None
    names = [raw_path] if raw_path.suffix else [raw_path.with_suffix(s) for s in suffixes]
    for name in names:
        # TeX normally resolves from the main project's working directory.  The
        # source-relative fallback supports explicitly local section layouts.
        for candidate in (manuscript_root / name, source.parent / name):
            if candidate.is_file():
                return candidate.resolve()
    return None


def scan_active_manuscript(project_root: Path) -> list[str]:
    """Audit the source and graphics dependency closure of overleaf/main.tex."""

    manuscript_root = (project_root / "overleaf").resolve()
    entrypoint = manuscript_root / "main.tex"
    if not entrypoint.is_file():
        return ["overleaf/main.tex: active manuscript entry point is missing"]

    violations: list[str] = []
    pending = [entrypoint.resolve()]
    visited: set[Path] = set()
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        visited.add(source)
        try:
            relative = source.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            violations.append(f"{source}: manuscript dependency escapes the project")
            continue
        try:
            source.relative_to(manuscript_root)
        except ValueError:
            violations.append(f"{relative}: manuscript dependency escapes overleaf/")
            continue

        violations.extend(_forbidden_path(relative, relative))
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            violations.append(f"{relative}: cannot audit manuscript source: {error}")
            continue
        violations.extend(scan_text(relative, text, tex=source.suffix.lower() == ".tex"))

        if source.suffix.lower() not in {".tex", ".md", ".txt"}:
            continue
        uncommented = _strip_tex_comments(text)
        for match in INPUT_RE.finditer(uncommented):
            raw_name = match.group(1).strip()
            violations.extend(_forbidden_path(relative, raw_name))
            dependency = _resolve_dependency(
                manuscript_root, source, raw_name, (".tex",)
            )
            if dependency is None:
                line = uncommented.count("\n", 0, match.start()) + 1
                violations.append(
                    f"{relative}:{line}: cannot audit missing TeX dependency: {raw_name}"
                )
            else:
                pending.append(dependency)

        for match in GRAPHICS_RE.finditer(uncommented):
            raw_name = match.group(1).strip()
            violations.extend(_forbidden_path(relative, raw_name))
            dependency = _resolve_dependency(
                manuscript_root,
                source,
                raw_name,
                (".pdf", ".png", ".jpg", ".jpeg", ".svg"),
            )
            if dependency is None:
                line = uncommented.count("\n", 0, match.start()) + 1
                violations.append(
                    f"{relative}:{line}: cannot audit missing graphic dependency: {raw_name}"
                )
            elif dependency.suffix.lower() == ".svg":
                pending.append(dependency)
    return violations


def scan_export_zips(project_root: Path) -> list[str]:
    """Audit textual members of every active Overleaf export ZIP."""

    violations: list[str] = []
    export_root = project_root / "overleaf" / "exports"
    for archive in sorted(export_root.glob("*.zip")):
        label = archive.relative_to(project_root).as_posix()
        try:
            with zipfile.ZipFile(archive) as handle:
                for member in handle.infolist():
                    if member.is_dir():
                        continue
                    member_label = f"{label}!{member.filename}"
                    violations.extend(_forbidden_path(member_label, member.filename))
                    suffix = Path(member.filename).suffix.lower()
                    # Bibliography databases and generated bibliography files are
                    # literature, not internal experiment provenance.
                    if suffix in {".bib", ".bbl"} or suffix not in TEXTUAL_EXPORT_SUFFIXES:
                        continue
                    try:
                        text = handle.read(member).decode("utf-8")
                    except (OSError, UnicodeError, RuntimeError) as error:
                        violations.append(f"{member_label}: cannot audit ZIP member: {error}")
                        continue
                    violations.extend(scan_text(member_label, text, tex=suffix == ".tex"))
        except (OSError, zipfile.BadZipFile) as error:
            violations.append(f"{label}: cannot audit export ZIP: {error}")
    return violations


def current_pdf_paths(project_root: Path) -> list[Path]:
    """Return manuscript PDFs from the sole canonical output directory."""

    return sorted(
        path for path in project_root.glob("output/pdf/*.pdf") if path.is_file()
    )


def misplaced_manuscript_pdf_paths(project_root: Path) -> list[Path]:
    """Return rendered manuscript PDFs found outside the canonical directory."""

    candidates: set[Path] = set()
    fixed = (
        project_root / "overleaf" / "main.pdf",
        project_root / "tmp" / "pdfs" / "acl2027-current" / "main.pdf",
    )
    candidates.update(path for path in fixed if path.is_file())
    for pattern in (
        "overleaf/exports/*.pdf",
        "overleaf/output/**/*.pdf",
        "tmp/**/*.pdf",
    ):
        candidates.update(path for path in project_root.glob(pattern) if path.is_file())
    return sorted(candidates)


def scan_pdf(path: Path, project_root: Path, pdftotext_path: str) -> list[str]:
    label = path.relative_to(project_root).as_posix()
    try:
        completed = subprocess.run(
            [pdftotext_path, str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return [f"{label}: cannot audit manuscript PDF: {error}"]
    if completed.returncode != 0:
        detail = _shorten(completed.stderr or "pdftotext failed")
        return [f"{label}: cannot audit manuscript PDF: {detail}"]
    return scan_text(label, completed.stdout)


def scan_regeneration_scripts(project_root: Path) -> list[str]:
    """Find active scripts capable of writing fictional results into overleaf/."""

    violations: list[str] = []
    resolved_self = SCRIPT_PATH.resolve()
    for directory, directory_names, file_names in os.walk(project_root):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(project_root)
        parts = relative_directory.parts
        if parts and parts[0] in SCRIPT_SCAN_IGNORED_TOP_LEVEL:
            directory_names[:] = []
            continue
        if len(parts) >= 2 and parts[:2] == ("governance", "tests"):
            directory_names[:] = []
            continue
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in SCRIPT_SCAN_IGNORED_DIRECTORY_NAMES
            and not (
                not parts and name in SCRIPT_SCAN_IGNORED_TOP_LEVEL
            )
        )
        for file_name in sorted(file_names):
            path = directory_path / file_name
            if path.suffix.lower() not in SCRIPT_SUFFIXES:
                continue
            relative_path = path.relative_to(project_root)
            if path.resolve() == resolved_self:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if not OVERLEAF_DESTINATION_RE.search(text):
                continue
            if not DATA_CLASS_RE.search(text):
                continue
            if not SCRIPT_WRITER_RE.search(text):
                continue
            overleaf_match = OVERLEAF_DESTINATION_RE.search(text)
            assert overleaf_match is not None
            line = text.count("\n", 0, overleaf_match.start()) + 1
            violations.append(
                f"{relative_path.as_posix()}:{line}: active script can write "
                "fictional/synthetic/demo results into overleaf/"
            )
    return violations


def audit_project(
    project_root: Path,
    *,
    pdftotext_path: str | None = None,
) -> tuple[list[str], int, bool]:
    """Run the full audit.

    Returns ``(violations, pdf_count, pdf_scan_available)``.  Passing an empty
    string disables PDF extraction for focused unit tests; ``None`` discovers
    ``pdftotext`` on PATH.
    """

    root = project_root.resolve()
    violations: list[str] = []
    violations.extend(scan_active_manuscript(root))
    violations.extend(scan_export_zips(root))
    violations.extend(scan_regeneration_scripts(root))

    misplaced_pdfs = misplaced_manuscript_pdf_paths(root)
    for path in misplaced_pdfs:
        label = path.relative_to(root).as_posix()
        violations.append(
            f"{label}: rendered manuscript PDFs must be stored only in output/pdf/"
        )

    pdfs = sorted(set(current_pdf_paths(root)) | set(misplaced_pdfs))
    tool = shutil.which("pdftotext") if pdftotext_path is None else pdftotext_path
    if tool:
        for path in pdfs:
            violations.extend(scan_pdf(path, root, tool))
    return sorted(set(violations)), len(pdfs), bool(tool)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed when fictional-data experiments reach manuscript artifacts."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root (defaults to the workspace containing this script)",
    )
    args = parser.parse_args(argv)

    violations, pdf_count, pdf_scan_available = audit_project(args.root)
    if pdf_count and not pdf_scan_available:
        print(
            "manuscript data-policy note: pdftotext is unavailable; PDF text was not audited",
            file=sys.stderr,
        )
    if violations:
        print("manuscript data policy rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("manuscript data policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
