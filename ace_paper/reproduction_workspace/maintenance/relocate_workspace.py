"""One-time relocation with content verification and legacy path aliases."""

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "reproduction_workspace"
ORIGINAL = ROOT / "original_sources"
MAPPINGS = []


def inventory(path):
    if path.is_file():
        return {".": hashlib.sha256(path.read_bytes()).hexdigest()}
    entries = {}
    for base, directories, files in os.walk(path):
        directories[:] = [name for name in directories if name != ".git"]
        for name in files:
            item = Path(base) / name
            key = str(item.relative_to(path))
            if item.is_symlink():
                entries[key] = "symlink:" + os.readlink(item)
            else:
                digest = hashlib.sha256()
                with item.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                entries[key] = digest.hexdigest()
    return entries


def relocate(source, destination):
    if not source.exists() or source.is_symlink() or destination.exists():
        raise RuntimeError(f"Unexpected migration state: {source} -> {destination}")
    before = inventory(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    source.symlink_to(os.path.relpath(destination, source.parent), target_is_directory=destination.is_dir())
    after = inventory(destination)
    if before != after:
        raise RuntimeError(f"Content verification failed: {destination}")
    MAPPINGS.append({"old_path": str(source), "new_path": str(destination),
                     "verified_files": len(before), "sha256_verified": True})
    (WORK / "maintenance/relocation_manifest.json").write_text(json.dumps(MAPPINGS, indent=2) + "\n")
    print(f"Verified {len(before)} files: {source.name} -> {destination}", flush=True)


def main():
    for name in ("paper_reproduction", "reproduction", "results", ".venv",
                 "BIOMEDICAL_PLAYBOOK_FEEDBACK_DESIGN.md", "PROVENANCE.json",
                 "REPRODUCTION_REPORT.md", "requirements-minimal.txt"):
        relocate(ROOT / name, WORK / name)
    relocate(ROOT / "upstream", ORIGINAL / "ace")
    (WORK / "upstream").symlink_to("../original_sources/ace", target_is_directory=True)
    sources = WORK / "paper_reproduction/sources"
    for name in ("stream-bench", "gepa-appworld", "project-page"):
        relocate(sources / name, ORIGINAL / name)
    relocate(sources / "ace-appworld-latest", WORK / "working_sources/ace-appworld-latest")
    relocate(WORK / "paper_reproduction/paper/ace_arxiv_2510.04618.pdf",
             ORIGINAL / "paper/ace_arxiv_2510.04618.pdf")
    source = WORK / "working_sources/ace-appworld-latest"
    destination = ORIGINAL / "ace-appworld"
    subprocess.run(["git", "clone", "--no-hardlinks", str(source), str(destination)], check=True)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "-C", str(destination), "checkout", "--detach", revision], check=True)
    subprocess.run(["git", "-C", str(destination), "remote", "set-url", "origin",
                    "https://github.com/ace-agent/ace-appworld.git"], check=True)
    if subprocess.check_output(["git", "-C", str(destination), "status", "--porcelain"], text=True).strip():
        raise RuntimeError("Pristine AppWorld checkout is not clean")
    print(f"Pristine AppWorld source verified at {revision}")


if __name__ == "__main__":
    main()
