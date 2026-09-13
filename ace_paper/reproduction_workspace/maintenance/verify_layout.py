"""Read-only checks for the separated ACE source and reproduction layout."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "reproduction_workspace"
ORIGINAL = ROOT / "original_sources"


def main():
    mappings = json.loads((WORK / "maintenance/relocation_manifest.json").read_text())
    for entry in mappings:
        old, new = Path(entry["old_path"]), Path(entry["new_path"])
        assert old.is_symlink() and old.resolve() == new.resolve(), entry
        assert new.exists(), entry
    revisions = {}
    for name in ("ace", "ace-appworld", "stream-bench", "gepa-appworld", "project-page"):
        path = ORIGINAL / name
        status = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True)
        assert not status.strip(), (name, status)
        revisions[name] = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    playbooks = {}
    for path in (ORIGINAL / "ace-appworld/experiments/playbooks").glob("*.txt"):
        working_copy = WORK / "working_sources/ace-appworld-latest/experiments/playbooks" / path.name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert hashlib.sha256(working_copy.read_bytes()).hexdigest() == digest, path
        playbooks[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    report = {
        "relocation_aliases_verified": len(mappings),
        "pristine_repositories": revisions,
        "published_playbooks_match_working_copy": playbooks,
        "finance_python_available": (WORK / "paper_reproduction/.venv-finance/bin/python").exists(),
        "preexisting_limitations": {
            "appworld_python_available": (WORK / "paper_reproduction/.venv-appworld/bin/python").exists(),
            "legacy_smoke_python_available": (WORK / ".venv/bin/python").exists(),
        },
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
