# ACE-Inspired Eight-Hour Execution

Date: 2026-09-10 KST. The user instructed starting the proposed four-dataset run
and producing the ACE method result table and Playbook results. The launch uses
the recommended existing-panel subset, preserving source separation except for
the previously authorized CaChe within-source diagnostic. Reused evaluation
items cannot later be described as untouched. No manuscript export is authorized.

## Executable scope

`run_ace_flaw_8h.py` implements the eight-hour v6 diagnostic with
`ace_flaw_contract.py` and the offline `plan_gemma_8h.py` helpers. Earlier design
files remain historical specifications. A run snapshots all three code files,
source selections, task payloads, prompt/schema contracts, and model digest.
Its immutable files and runtime_config.json govern that run.

- Local Gemma 3 4B for all calls. No API charges or downloads.
- Four datasets, ten development and twenty evaluation packets each.
- Detector + Finalizer; one structured Learning Editor and at most one separate
  Patch Auditor on each development exposure. Three epochs with isolated memory.
- Same twenty evaluation packets at seed E0 and E3, with budget-labeled common-
  epoch fallback if development hits its reserved deadline.
- One judgment call returns both Credibility and Conformability. Null remains
  unresolved, and complete bad quotations remain visible for judgment.
- Final requested table: four rows, method labeled ACE-inspired WarrantRoute-Lite.
  This is not the original ACE benchmark, full WarrantRoute, or repair validation.

Actual decoding is frozen as temperature 0, seed 20260910, num_ctx 32768,
num_predict 4096. The local model reports a larger supported context. Complete
requests additionally pass a conservative byte-based admission bound including
schema/output reserves. This bound can reject a request that a tokenizer would
fit; it never silently shortens source text or memory. Later oversized learning
requests become visible technical holds without fabricated patches.

Each reusable rule field is at most 240 characters and their sum at most 640.
Forty active rules and six retrieved rules remain the caps. These are newly
frozen execution limits, not measured optimal settings. Builder candidate_role
is excluded from reviewer input. Original source text, order, source metadata
and legitimate local context are preserved in the restricted task artifacts.

## Safety and resumption

Supervisor, worker and project-wide run locks prevent duplicate instances of
this executor. Source/implementation/model hashes are checked before launch.
Requests and raw responses are durable and immutable. Existing identified calls
are reused on resume, never submitted twice. Ambiguous dispatch stops the run;
there is no automatic retry. Do not restart a terminal run or change a frozen
prompt after seeing an unfavorable output.

The eight-hour clock starts at supervisor launch and cannot reset on resume.
Development stops admission near 3:30; complete core evaluation/judging has
priority afterward. Inference admission stops at 7:45 and finalization is reserved
to 8:00. Each new request needs at least 181 seconds of phase budget, accounting
for its 180-second timeout. Client timeouts are ambiguous backend state, not
proof that inference stopped. Do not kill the global Ollama service or other work.

Technical review/learning/judge failures are distinct from valid false/null
judgments, no-op learning and withheld patches. Three consecutive technical
trajectories stop for diagnosis. References are provisional same-model outputs;
incomplete reference coverage is not verified negative ground truth.

## Artifacts

- `results_table_ACE.csv` and `.md`: requested four-dataset adapted result table.
- `dataset_quality.csv`: matched seed and adapted rows with T/F/null/technical/
  unprocessed counts, resolved-case percentages, full-panel percentages and coverage.
- `paired_changes.csv`: differences on jointly binary matched packet pairs only.
- `fixed_probe_curve.csv`: the same five evaluation packets at available checkpoints.
- `playbook_result.csv` and `.md`: creation, audit, support and retrieval summary.
- `playbooks/<dataset>/current.json/.md`, complete-epoch snapshots, and immutable
  update diffs. Raw development results link each edit to its exact audit.
- `calls/`, `predictions/`, `references/`, `results/`, `status.json`, and the
  terminal `final_manifest.json` with derived-file hashes.

Only derived progress/export files are replaced. Original reviewer outputs,
locked diagnoses, reference records and raw call journals are not overwritten.
The original n100 Table 3 and manuscript are never changed by this executor.

## Commands

From the ACL 2027 project root, use a new private Storage run directory:

```sh
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/run_ace_flaw_8h.py prepare --run-dir RUN_DIRECTORY
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/run_ace_flaw_8h.py run --run-dir RUN_DIRECTORY
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/run_ace_flaw_8h.py status --run-dir RUN_DIRECTORY
```

`prepare` checks and freezes inputs and creates empty tables without inference.
`run` starts the clock and supervisor. `status` is read-only and cannot start,
repair or resume inference. Do not run placeholder commands on an existing run.

Offline tests cover schema/identity handling, matched evaluation, read-only
evaluation memory, audit refusal, immutable writes, timeout ambiguity, and a
complete mocked schedule. Mocked results are software tests only and are never
copied into actual tables or treated as experiment evidence.
