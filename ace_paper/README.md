# ACE: original sources and reproduction work

There are two canonical locations. Use these paths for new work:

| Directory | Ownership and purpose |
| --- | --- |
| `original_sources/` | Pristine official Git checkouts and the downloaded paper PDF |
| `reproduction_workspace/` | Locally written scripts, experiments, outputs, environments, notes, and patched working sources |

## Authors' published playbooks

Open `original_sources/ace-appworld/experiments/playbooks/`.

- `appworld_offline_trained_no_gt_playbook.txt`: authors' released offline result.
- `appworld_online_trained_playbook.txt`: authors' released online result.
- `appworld_initial_playbook.txt`: authors' initial instructions.
- `appworld_offline_trained_with_gt_playbook.txt`: empty in the pinned release.

These are not locally trained Qwen outputs.

## Local reproduction files

- `reproduction_workspace/paper_reproduction/scripts/`: local runners and adapters.
- `reproduction_workspace/paper_reproduction/model_comparison/`: local model runs and learned playbooks.
- `reproduction_workspace/paper_reproduction/runs/`: paper-target runs, supervision status, and preflight reports.
- `reproduction_workspace/working_sources/ace-appworld-latest/`: original AppWorld checkout plus the recorded compatibility patch and runtime data.
- `reproduction_workspace/reproduction/` and `results/`: historical local smoke experiment.
- `reproduction_workspace/BIOMEDICAL_PLAYBOOK_FEEDBACK_DESIGN.md`: locally written design proposal.
- `reproduction_workspace/maintenance/`: relocation manifest and verification report.

## Legacy path aliases

The old top-level `paper_reproduction`, `upstream`, `reproduction`, `results`,
`.venv`, and document paths are symbolic links, not duplicate datasets or new
sources. They preserve old absolute paths in logs, links, virtual-environment
entry points, and launch commands. Do not remove them without migrating those
references. Physical files are stored under the two canonical directories.

The `sources/` paths used by existing runners likewise resolve to official
checkouts or the explicitly separated patched working checkout. Historical
experiment records are preserved rather than rewriting their provenance.
