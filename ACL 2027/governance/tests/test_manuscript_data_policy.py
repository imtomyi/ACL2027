from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


GOVERNANCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = GOVERNANCE_ROOT / "scripts" / "check_manuscript_data_policy.py"

SPEC = importlib.util.spec_from_file_location("check_manuscript_data_policy", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class ManuscriptDataPolicyTests(unittest.TestCase):
    def make_project(self, root: Path, section: str = "Approved real-data results.\n") -> None:
        (root / "overleaf" / "sections").mkdir(parents=True)
        (root / "overleaf" / "exports").mkdir(parents=True)
        (root / "overleaf" / "main.tex").write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{sections/paper}\n"
            "\\bibliography{custom}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        (root / "overleaf" / "sections" / "paper.tex").write_text(
            section, encoding="utf-8"
        )
        (root / "overleaf" / "custom.bib").write_text(
            "@article{prior, title={A Synthetic Dataset and Its Benchmark Results}}\n",
            encoding="utf-8",
        )

    def audit(self, root: Path) -> list[str]:
        violations, _pdf_count, _pdf_available = policy.audit_project(
            root, pdftotext_path=""
        )
        return violations

    def test_clean_real_data_source_ignores_literature_and_storage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(
                root,
                "We will use simulation-based power analysis. "
                "Prior work reports results for a synthetic benchmark.\n",
            )
            archived = root / "Storage" / "synthetic-results" / "archived"
            archived.mkdir(parents=True)
            (archived / "rebuild.py").write_text(
                'target = ROOT / "overleaf" / "tables" / "synthetic.tex"\n'
                'target.write_text("fictional experiment results")\n',
                encoding="utf-8",
            )
            self.assertEqual(self.audit(root), [])

    def test_active_synthetic_table_dependency_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(
                root,
                "\\input{tables/synthetic_paper_metrics}\n",
            )
            tables = root / "overleaf" / "tables"
            tables.mkdir()
            (tables / "synthetic_paper_metrics.tex").write_text(
                "Approved-looking values.\n", encoding="utf-8"
            )
            violations = self.audit(root)
            self.assertTrue(any("forbidden fictional-result" in row for row in violations))

    def test_neutral_filename_with_fictional_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, "\\input{tables/results}\n")
            tables = root / "overleaf" / "tables"
            tables.mkdir()
            (tables / "results.tex").write_text(
                "% data_origin=fictional\n"
                "\\begin{table}\\caption{Results}\\end{table}\n",
                encoding="utf-8",
            )
            violations = self.audit(root)
            self.assertTrue(any("provenance declaration" in row for row in violations))

    def test_internal_fictional_experiment_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(
                root,
                "Our experiment reports model rankings from a fictional dataset.\n",
            )
            violations = self.audit(root)
            self.assertTrue(any("internal fictional" in row for row in violations))

    def test_explicit_exclusion_statement_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(
                root,
                "\\caption{Synthetic qualification results are excluded.}\n",
            )
            self.assertEqual(self.audit(root), [])

    def test_stale_export_zip_text_and_member_name_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            archive = root / "overleaf" / "exports" / "submission.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr(
                    "sections/paper.tex",
                    "The current manuscript reports a synthetic experiment result.\n",
                )
                handle.writestr("tables/synthetic_metrics.tex", "values\n")
            violations = self.audit(root)
            self.assertTrue(any("submission.zip!sections/paper.tex" in row for row in violations))
            self.assertTrue(any("submission.zip!tables/synthetic_metrics.tex" in row for row in violations))

    @mock.patch.object(policy.subprocess, "run")
    def test_current_pdf_text_is_rejected(self, run: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            output = root / "output" / "pdf"
            output.mkdir(parents=True)
            pdf = output / "warrant-route-acl2027-current-manuscript.pdf"
            pdf.write_bytes(b"%PDF-placeholder")
            run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="The current manuscript reports results from a fictional dataset.\n",
                stderr="",
            )
            violations, pdf_count, pdf_available = policy.audit_project(
                root, pdftotext_path="pdftotext"
            )
            self.assertEqual(pdf_count, 1)
            self.assertTrue(pdf_available)
            self.assertTrue(
                any(
                    "output/pdf/warrant-route-acl2027-current-manuscript.pdf" in row
                    for row in violations
                )
            )

    def test_misplaced_manuscript_pdf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            (root / "overleaf" / "main.pdf").write_bytes(b"%PDF-placeholder")
            violations = self.audit(root)
            self.assertTrue(
                any(
                    "overleaf/main.pdf: rendered manuscript PDFs must be stored only"
                    in row
                    for row in violations
                )
            )

    def test_temporary_rendered_pdf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            temporary = root / "tmp" / "pdfs" / "build"
            temporary.mkdir(parents=True)
            (temporary / "main.pdf").write_bytes(b"%PDF-placeholder")
            violations = self.audit(root)
            self.assertTrue(
                any(
                    "tmp/pdfs/build/main.pdf: rendered manuscript PDFs must be stored only"
                    in row
                    for row in violations
                )
            )

    def test_figure_pdf_is_exempt_from_manuscript_location_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            figures = root / "overleaf" / "figures"
            figures.mkdir()
            (figures / "framework.pdf").write_bytes(b"%PDF-placeholder")
            self.assertEqual(self.audit(root), [])

    def test_active_regeneration_script_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            scripts = root / "experiments" / "qualification" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "aggregate.py").write_text(
                'target = ROOT / "overleaf" / "tables" / "results.tex"\n'
                'payload = "synthetic experiment results"\n'
                "target.write_text(payload)\n",
                encoding="utf-8",
            )
            violations = self.audit(root)
            self.assertTrue(any("active script can write" in row for row in violations))


if __name__ == "__main__":
    unittest.main()
