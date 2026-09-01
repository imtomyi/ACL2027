#!/usr/bin/env python3
"""Require a stable set of publications to remain cited in the manuscript."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]

REQUIRED_CITATIONS = {
    "xu2026tama": "TAMA",
    "yi2024protomed": "ProtoMed-LLM",
    "yi2025autota": "Auto-TA",
    "yi2025sftta": "SFT-TA",
    "yi2025position": "Position: Thematic Analysis of Unstructured Clinical Transcripts with Large Language Models",
    "yi2026provenance": "Automated Thematic Analysis for Clinical Qualitative Data: Iterative Codebook Refinement with Full Provenance",
}

INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
CITATION_RE = re.compile(
    r"\\cite(?:p|t|alp|alt|author|year|yearpar)?\*?"
    r"(?:\s*\[[^\]]*\]){0,2}\s*\{([^{}]+)\}"
)
BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)


class CitationCheckError(RuntimeError):
    """Raised when the active manuscript dependency graph cannot be audited."""


def strip_tex_comments(text: str) -> str:
    """Remove unescaped percent comments before dependency/citation parsing."""

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


def resolve_tex_reference(overleaf_root: Path, current: Path, reference: str) -> Path | None:
    path = Path(reference.strip())
    if not path.suffix:
        path = path.with_suffix(".tex")
    for candidate in (current.parent / path, overleaf_root / path):
        if candidate.is_file():
            return candidate.resolve()
    return None


def active_tex_sources(main_tex: Path) -> set[Path]:
    """Return the recursive input/include closure rooted at main.tex."""

    if not main_tex.is_file():
        raise CitationCheckError(f"active manuscript entry point missing: {main_tex}")
    overleaf_root = main_tex.parent.resolve()
    pending = [main_tex.resolve()]
    visited: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        try:
            text = strip_tex_comments(current.read_text(encoding="utf-8"))
        except OSError as error:
            raise CitationCheckError(f"active TeX source unreadable: {current}: {error}") from error
        for reference in INPUT_RE.findall(text):
            resolved = resolve_tex_reference(overleaf_root, current, reference)
            if resolved is None:
                raise CitationCheckError(
                    f"active TeX dependency missing: {reference} referenced from {current}"
                )
            if resolved not in visited:
                pending.append(resolved)
    return visited


def cited_keys(sources: set[Path]) -> set[str]:
    keys: set[str] = set()
    for source in sources:
        text = strip_tex_comments(source.read_text(encoding="utf-8"))
        for citation_group in CITATION_RE.findall(text):
            keys.update(key.strip() for key in citation_group.split(",") if key.strip())
    return keys


def bibliography_keys(bibliography: Path) -> set[str]:
    return set(BIB_ENTRY_RE.findall(bibliography.read_text(encoding="utf-8")))


def audit_project(project_root: Path) -> list[str]:
    overleaf_root = project_root / "overleaf"
    try:
        sources = active_tex_sources(overleaf_root / "main.tex")
    except CitationCheckError as error:
        return [str(error)]
    citations = cited_keys(sources)
    bibliography_path = overleaf_root / "custom.bib"
    if not bibliography_path.is_file():
        return [f"active bibliography missing: {bibliography_path}"]
    try:
        bibliography = bibliography_keys(bibliography_path)
    except OSError as error:
        return [f"active bibliography unreadable: {bibliography_path}: {error}"]
    violations: list[str] = []
    for key, title in REQUIRED_CITATIONS.items():
        if key not in bibliography:
            violations.append(f"required bibliography entry missing: {key} ({title})")
        if key not in citations:
            violations.append(f"required active-manuscript citation missing: {key} ({title})")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Require six publications to remain cited in active manuscript source."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="project root containing overleaf/main.tex (default: repository root)",
    )
    args = parser.parse_args(argv)
    violations = audit_project(args.root.resolve())
    if violations:
        print("required manuscript citation check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print(f"required manuscript citations passed ({len(REQUIRED_CITATIONS)}/{len(REQUIRED_CITATIONS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
