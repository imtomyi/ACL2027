# WarrantRoute Flaw-Detection Design and Planning

## Next Design: Review TA Codes and Themes

The [TA-artifact flaw-detection guideline](../../Storage/experiment_guidelines/ace_ta_artifact_flaw_detection_v1.md)
adds one TA Analyst role to generate and lock evidence-linked codes and provisional
themes. The existing detector then reviews those artifacts against their source
data; the Reflector/Curator and rule auditor update a detection Playbook during
three development epochs. Generation is cached so reviewer conditions receive
the same TA artifact. TA-artifact quality and flaw-review correctness/quality are
separate evaluation objects.

The complete scored comparison remains prospective, not permission for a full
experiment. TA-target gold matching and validated evaluation exports are still
required. The separately authorized narrow smoke runners below implement
construction and unscored adaptive review. Historical claim/paragraph protocols
remain reproducibility records and do not become TA experiments.
The paused paragraph replay and all automatic/manual Playbook files are unchanged.

A separate [12-point TA generation smoke test](../../Storage/experiment_guidelines/ta_generation_12_smoke_v1.md)
now implements construction only: three original four-paragraph Dreaddit packets,
one local Gemma call per packet, locked codes/themes, source anchors and readable
reports. `run_ta_generation_smoke.py --help` lists prepare/run/status/pause commands.
It does not run flaw detection, judge quality or update a Playbook, and does not
make the full prospective protocol executable.

The [12-point TA Playbook continuation](../../Storage/experiment_guidelines/ta_playbook_12_smoke_v1.md)
uses those three locked artifacts across three epochs. It runs TA-target flaw
detection, merged reflection/curation, and audits eligible deltas before publishing
numbered TXT Playbooks for the next query. `run_ta_playbook_smoke.py --help`
lists prepare/run/status/pause commands. This is an unscored development test,
not an implementation of the full gold-qualified study or evidence of improvement.

The [V2 admission/interface revision](../../Storage/experiment_guidelines/ta_playbook_12_relaxed_v2.md)
allows useful concrete elaborations of existing guidance without requiring a new
mechanism. Grounding, reusability, counterconditions, no invention/leakage and no
contradictions remain mandatory. Operation-specific learning schemas prevent
invalid add targets, and artifact slots constrain field identities. The separate
`run_ta_playbook_relaxed.py` controller preserves frozen V1 code and results.
This revision does not automatically launch inference or approve old candidates.

## Detection-First Revision: Not Launched

The latest objective requires correct flaw type, target, mechanism and evidence,
not generic review plausibility. The [v2 scoring protocol](../../Storage/experiment_guidelines/ace_claim_detection_v2.md)
governs newly prepared online runs. `strict_flaw_scoring.py` provides one-to-one
TP/FP/FN scoring, per-type metrics and separately named detection-gated C/F
composites. A complete adjudicated gold bank is required before inference.
Existing generator-intended labels alone do not satisfy this requirement.
No historical result or frozen experiment has been changed or resumed.

Current source also publishes numbered TXT Playbooks: each corpus has
`playbooks/<dataset>/current.txt`, immutable revision history and a hash manifest.
The same TXT projection is sent to the model, and locked predictions retain the
retrieved text. See the TXT section of the v2 protocol above. This serialization
revision requires a fresh preparation; it does not alter a frozen old run.

## Historical Online v1: Not Launched

The [online system and experiment design](../../Storage/experiment_guidelines/ace_claim_online_v1.md)
records the preceding version, superseded for future execution by v2 above.
Its prepared snapshot retains the old code. Each stream prediction and judgment is locked before
source-grounded Reflector/Curator updates. Per-edit auditing supports new rules,
refinement and explicit reinforcement. The next detector receives retrieved
rules and records their application. References and quality scores never enter
the updater. A matched static-seed arm and coverage-aware learning curves are
exported separately from historical Table 3.

The old expansion is paused; none of its frozen code, results, memory or clock
is changed. New preparation imports only its frozen inputs, labels their prior
exposure, and makes no Ollama/API call. Live semantic preflight and launch remain
pending. Run `run_ace_flaw_online.py --help` for prepare/status/pause/run/resume
commands. Inference requires explicit authorization and the shared execution
lock; a suspended legacy process still holding that lock blocks the new runner.

## Same-Protocol Data Expansion

The user requested more data on 2026-09-10. The
[expansion protocol and withholding analysis](../../Storage/experiment_guidelines/ace_flaw_expansion_20260910.md)
specify ten new development and eighty new evaluation packets for each corpus.
The v2 prompts, semantic contract, Gemma model and scoring remain unchanged.
This produces 120 development exposures and 640 core reviews, with at most 2,880
local calls including optional probes, under a separate eight-hour budget.
The completed v2 run below is historical. Its outputs are preserved, not merged.

## Initial Eight-Hour Run

The newly authorized run is the
[eight-hour, four-corpus Gemma diagnostic](../../Storage/experiment_guidelines/warrantroute_flaw_detection_8h_v6.md).
It prioritizes per-corpus Credibility/Conformability and audited Playbook creation
and retrieval on matched E0/adapted panels. It has an eight-hour hard budget,
1,080 mandatory calls at most, and 120 optional calls. On 2026-09-10 the user
instructed starting the proposed experiment and generating four-dataset ACE and
Playbook result tables. The executable implementation and frozen limits are in
[ace_8h_execution.md](ace_8h_execution.md). It uses the recommended existing-panel
subset; selected items are reused diagnostics, not untouched future test data.
Historical planning JSON retains its original pending-decision state; the run's
authorization record records the later launch instruction.

The 2026-09-10 restart uses the identity-bound v2 transport documented in
[ace_8h_execution.md](ace_8h_execution.md). It bounds free-text fields, binds
Finalizer/judge/auditor identities to their inputs, and preserves rejected
Playbook updates without technical retries. `smoke_ace_flaw_8h.py` tests eight
development packets across all four corpora before an explicitly authorized
fresh run. The earlier stopped runs and smoke outputs are never merged into
its result table. See the
[launch record](../../Storage/experiment_guidelines/warrantroute_flaw_detection_8h_launch_record.md)
for the actual current run and status.

Check its budget and optional read-only candidate selection:

```sh
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/plan_gemma_8h.py --audit-candidates
```

The larger prospective comparison remains the
[final v5 protocol](../../Storage/experiment_guidelines/warrantroute_flaw_detection_final_protocol_v5.md),
with [role prompt contracts](../../Storage/experiment_guidelines/warrantroute_flaw_detection_prompts_v5.md)
and a [machine-readable plan](../../Storage/experiment_guidelines/warrantroute_flaw_detection_v5.plan.json).
The purpose is detecting and characterizing flaws in supplied claims, not
generating themes or repairing documents. The design is finalized. The full
runner, input qualification, and experiment are not complete or authorized.

The v5 main design separates a four-method comparison from three component
contrasts: explicit reflection, multiple development epochs, and delta updates.
Its single-order main study is not an eight-hour run. The earlier four-hour
pilot is superseded as a next-run proposal by v6, not silently changed in code.

The files below retain their historical v4 / pilot-v1 behavior. In particular,
the existing pilot still selects four corpora and forces binary quality labels.
It is NOT a v5 runner. Do not launch it as v5 without the listed integration gates.

## Earlier Implementation Scope

The v4 multi-epoch files are an offline candidate scheduler and configuration,
not a full-experiment inference runner. They make no Ollama/API calls, train no
weights and cannot resume the stopped thematic-analysis experiment.

A separate [Gemma four-hour Lite pilot](gemma_4h_pilot.md) now has a bounded
local inference runner, `gemma_4h_pilot.py`. It is a narrower claim-sentence
feasibility experiment with one model, no baselines and same-model judging.
It does not implement or replace the full v4 experiment.

The [historical v4 protocol](../../Storage/experiment_guidelines/warrantroute_claim_detection_multi_epoch_v4.md)
retains its old five-call review / three-extra-call default for reproducibility.
V5 instead specifies one Learning Editor with an explicit reflection function,
plus matched ablations. This design choice has not silently changed that code.

## Offline Checks

Check v5 scope, checkpoint reuse, and workload arithmetic without inference:

```sh
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/check_design_v5.py
```

This check is not data qualification, prompt-runtime equivalence, a semantic
scoring test, a launch command, or proof that the experiments will succeed.

From the `ACL 2027` project directory:

```sh
/opt/anaconda3/bin/python3 -B -m unittest discover -s experiments/warrantroute_claim_detection -p 'test_*.py' -v
```

Inspect a candidate schedule from historical packet IDs without writing files:

```sh
/opt/anaconda3/bin/python3 -B experiments/warrantroute_claim_detection/plan_multi_epoch.py --candidate-inputs Storage/rq2_personal_local_diagnostic/warrantroute_ace_ta/ace_ta_merged_20260909_v6/inputs.private.json
```

An optional `--output` creates a new JSON file under project Storage and refuses
to overwrite an existing file. Historical input payloads are not forwarded to
reviewers; only candidate IDs are selected. Claim eligibility and source-aware
probe selection are still pending. Generated counts describe planned work, not
finished predictions, valid judgments or an active execution queue.
