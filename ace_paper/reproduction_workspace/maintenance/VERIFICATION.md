# Relocation verification (2026-09-08)

Completed checks:

- No ACE experiment or supervisor process was running before relocation.
- SHA-256 inventories matched before and after each of the 14 recorded moves.
- All 14 recorded legacy aliases resolve to the intended new paths.
- All five checkouts in `original_sources/` have clean Git working trees.
- Original ACE and its pinned AppWorld submodule still resolve at their expected commits.
- The separate pristine AppWorld checkout matches the patched working checkout's commit.
- All four published AppWorld playbook files match between pristine and working copies.
- Structural preflight passes, including paper hash, repository revisions, dataset counts, and the preserved compatibility patch.
- The historical smoke-result verifier passes, including all three ACE role logs and applied deltas.
- The relocated Finance Python can import the official ACE components and read all 500 Formula training records.
- The local model runner's CLI works at the canonical path.
- The old Finance pip entry point resolves through its original shebang path.
- Both paper-table shell launchers pass `bash -n`.

No model inference, adaptation, or benchmark rerun was performed for this
directory-organization task. Historical logs and result provenance were not
rewritten. The structural preflight report was regenerated at its usual path.

Pre-existing limitations observed before moving files:

- The AppWorld virtual environment contains no Python or CLI executable.
- The historical smoke virtual environment contains no Python executable.
- The Finance environment is available; its interpreter is Python 3.14.

These missing environments were not caused by relocation. AppWorld execution
and the old smoke launch command need environment restoration before use.
The old smoke *artifacts* were successfully verified using the Finance Python.

Run `verify_layout.py` with the Finance Python for read-only layout checks.
`relocate_workspace.py` is a one-time migration record, not a normal launcher.
