# Restricted local policy records

The active `project_governance.local.json` record uses
`personal_local_only`. That mode removes the ten external gates from the
personal experiment path while keeping all cloud, human-review, publication,
submission, redistribution, and release capabilities disabled.

Run the personal readiness check with an explicit current UTC timestamp:

```bash
python3 governance/scripts/check_project_readiness.py \
  --record governance/local/project_governance.local.json \
  --as-of <CURRENT-UTC-TIMESTAMP> \
  --output governance/local/readiness_report.local.json
```

`personal_local_scope_eligible`, not `real_text_ready`, identifies the corpora
declared in scope for the private local experiment. It is not an execution
approval or live-file check. The separate personal-local policy validator must
bind the exact files and hashes before execution. `real_text_ready` remains
false by design.

The reviewer registry and privacy log are inactive in personal-local mode
because human exposure is prohibited. They remain available only for a future
formal workflow.

## Future formal workflow

This directory is also the only repository-adjacent location accepted by the
formal project-wide readiness checker for completed governance evidence. Its
contents are ignored except for this README and `.gitignore`.

Before adding evidence:

1. Restrict the directory to the local user (`0700`).
2. Copy, do not edit in place, the three tracked templates to these fixed local names:
   - `project_governance.local.json`
   - `reviewer_registry.local.json`
   - `privacy_review_log.local.json`
3. Restrict each local file to the local user (`0600`).
4. Store documentary references and versions, not source text, raw participant identifiers, access tokens, provider keys, reviewer names, emails, signatures, or identity crosswalk contents.
5. Keep reviewer names and contact details in an institutionally approved identity system. Refer to them here only through `REV_...` pseudonyms and a restricted crosswalk reference.
6. Do not change a gate to `approved` until its evidence is signed or otherwise final, its scope includes the exact corpus/use, and its approval/version dates are current.
7. For a future formal workflow, change `gate_mode` to `real_text_candidate`
   only as a deliberate final enablement step after the applicable evidence is
   recorded; the checker still requires all ten formal gates before declaring
   any formal real-text lane ready.

Example formal check:

```bash
chmod 700 governance/local
chmod 600 governance/local/*.local.json
python3 governance/scripts/check_project_readiness.py \
  --record governance/local/project_governance.local.json \
  --reviewer-registry governance/local/reviewer_registry.local.json \
  --privacy-log governance/local/privacy_review_log.local.json \
  --as-of 2026-08-25T00:00:00Z \
  --output governance/local/readiness_report.local.json
```

The formal report is a mechanical evidence check, not an approval. A failed or
missing formal gate means stop before using the human, cloud, publication, or
release workflow.
