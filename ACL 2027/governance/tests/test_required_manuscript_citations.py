from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


GOVERNANCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = GOVERNANCE_ROOT / "scripts" / "check_required_manuscript_citations.py"

SPEC = importlib.util.spec_from_file_location("check_required_manuscript_citations", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class RequiredManuscriptCitationTests(unittest.TestCase):
    def make_project(self, root: Path, paper_text: str) -> None:
        sections = root / "overleaf" / "sections"
        sections.mkdir(parents=True)
        (root / "overleaf" / "main.tex").write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{sections/paper}\n"
            "\\bibliography{custom}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        (sections / "paper.tex").write_text(paper_text, encoding="utf-8")
        entries = "\n".join(
            f"@article{{{key}, title={{{title}}}}}" 
            for key, title in checker.REQUIRED_CITATIONS.items()
        )
        (root / "overleaf" / "custom.bib").write_text(entries + "\n", encoding="utf-8")

    def all_citations(self) -> str:
        keys = ",".join(checker.REQUIRED_CITATIONS)
        return f"Required related work \\citep{{{keys}}}.\n"

    def test_all_required_active_citations_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "\\input{nested}\n")
            (root / "overleaf" / "sections" / "nested.tex").write_text(
                self.all_citations(), encoding="utf-8"
            )
            self.assertEqual(checker.audit_project(root), [])

    def test_missing_required_citation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = next(iter(checker.REQUIRED_CITATIONS))
            keys = [key for key in checker.REQUIRED_CITATIONS if key != missing]
            self.make_project(root, f"Related work \\citep{{{','.join(keys)}}}.\n")
            violations = checker.audit_project(root)
            self.assertTrue(any(missing in violation for violation in violations))

    def test_unreferenced_file_does_not_satisfy_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "Active prose without citations.\n")
            (root / "overleaf" / "sections" / "unused.tex").write_text(
                self.all_citations(), encoding="utf-8"
            )
            violations = checker.audit_project(root)
            self.assertEqual(len(violations), len(checker.REQUIRED_CITATIONS))

    def test_commented_citation_does_not_satisfy_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            keys = ",".join(checker.REQUIRED_CITATIONS)
            self.make_project(root, "% " + self.all_citations() + f"\\nocite{{{keys}}}\n")
            violations = checker.audit_project(root)
            self.assertEqual(len(violations), len(checker.REQUIRED_CITATIONS))

    def test_even_backslashes_before_percent_start_a_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "\\\\% " + self.all_citations())
            violations = checker.audit_project(root)
            self.assertEqual(len(violations), len(checker.REQUIRED_CITATIONS))

    def test_escaped_percent_does_not_hide_active_citations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "Literal \\% sign. " + self.all_citations())
            self.assertEqual(checker.audit_project(root), [])

    def test_missing_active_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "\\input{missing}\n" + self.all_citations())
            violations = checker.audit_project(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("active TeX dependency missing", violations[0])


if __name__ == "__main__":
    unittest.main()
