# ACE Paper Reproduction Status

## Scope

This workspace reproduces the released ACE paper only. Every source, dataset,
environment, patch, command, and output is contained under `ace_paper/`. No
other ACL2027 experiment, result, or manuscript is read, imported, changed, or
used for comparison.

## Paper targets

The primary targets are Table 1 (AppWorld) and Table 2 (Finance) from the ICLR
2026 paper. Exact values and shared settings are frozen in `targets.json`.

The paper uses the non-thinking DeepSeek-V3.1 model for the Generator,
Reflector, and Curator, batch size 1, up to 5 Reflector rounds, and up to 5
offline epochs. AppWorld is scored with TGC and SGC on `test_normal` and
`test_challenge`; Finance uses exact-match accuracy on FiNER and Formula.

## Completed setup

- Downloaded the arXiv v3 paper PDF and extracted text; SHA-256 is recorded.
- Cloned and pinned the official ACE repository and its ACE-AppWorld submodule.
- Checked out the latest public ACE-AppWorld revision separately because it
  contains fixes and files absent from the paper-pinned submodule.
- Cloned the publicly linked StreamBench, GEPA-AppWorld, and project-page repos.
- Downloaded official AppWorld data and released baseline outputs.
- Installed isolated AppWorld and Finance Python environments.
- Downloaded the `all-mpnet-base-v2` deduplication model into an isolated cache.
- Verified all 1,553 AppWorld app tests, all 139 package tests, and all 147 tasks.
- Recorded the one compatibility patch in `patches/appworld-evaluate-return.patch`.
- Added paper-table launchers that refuse to mix an existing run directory with
  a new run.

## Exact execution status

No headline number has been claimed as reproduced yet. The host does not
currently expose `SAMBANOVA_API_KEY`, which is required by the released configs
for the paper's DeepSeek-V3.1 model. A local model is deliberately not used as a
substitute.

Structural validation:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/preflight.py
```

Credential-gated validation:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/preflight.py --require-api
```

After an authorized key is present, individual rows are launched explicitly:

```bash
paper_reproduction/scripts/run_table2_finance.sh offline_gt_finer
paper_reproduction/scripts/run_table2_finance.sh offline_gt_formula
paper_reproduction/scripts/run_table1_appworld.sh released_offline_no_gt_eval
paper_reproduction/scripts/run_table1_appworld.sh offline_gt_full
```

The Table 1 online launchers initialize from the released offline no-GT
playbook, matching the paper's “ACE + offline warmup” row in Table 3.

## Public-release gaps

These are differences between the paper description and the public artifacts,
not changes made to the method here:

- The ACE repository cannot be installed editable as released because its
  packaging configuration discovers multiple top-level packages. The Finance
  environment therefore installs its declared dependencies and imports the
  checkout through `PYTHONPATH`.
- ACE-AppWorld configs refer to a nonexistent
  `appworld_offline_trained_no_gt_playbook_deepseek_3_1.txt`; the released file
  is `appworld_offline_trained_no_gt_playbook.txt`. Launchers override only this
  path.
- The released AppWorld with-GT playbook is empty, so that row must be adapted
  again before evaluation.
- Released AppWorld adaptation configs specify one epoch. Offline launchers
  override this to the paper's maximum of five epochs.
- The latest AppWorld library returned an evaluator tuple where its public API
  and tests expect a `TestTracker`. The minimal recorded patch restores that
  contract; all AppWorld tests pass afterward.
- The single-sample AppWorld path implements append-only `ADD` operations. Its
  later bullet-point analyzer is wired only to the parallel path, while the
  paper specifies batch size 1 and describes grow-and-refine deduplication.
  This prevents claiming perfect code-level equivalence for that component.
- The paper reports DDXPlus and BIRD-SQL appendix results, but the public ACE
  repository does not provide ACE runners/configs for those two benchmarks.
  StreamBench is preserved as the linked benchmark source, but those rows are
  not executable from the released ACE code alone.
- A standalone DeepSeek-V3.1 ReAct-base AppWorld config is not included in the
  released ACE-AppWorld configs. The target is recorded, but the base row cannot
  be rerun from the ACE release without reconstructing an unprovided config.

## Archived artifacts

The root-level `reproduction/`, `results/`, and `REPRODUCTION_REPORT.md` are an
older local-model mechanism smoke test. They remain only for provenance and are
excluded from this reproduction and every paper-result claim.
