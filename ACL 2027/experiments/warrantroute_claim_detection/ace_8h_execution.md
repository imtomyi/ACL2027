# ACE-Inspired Eight-Hour Execution

Date: 2026-09-10 KST. The user instructed starting the proposed four-dataset run
and producing the ACE method result table and Playbook results. The launch uses
the recommended existing-panel subset, preserving source separation except for
the previously authorized CaChe within-source diagnostic. Reused evaluation
items cannot later be described as untouched. No manuscript export is authorized.

## Executable scope

The later same-protocol expansion is documented in
`Storage/experiment_guidelines/ace_flaw_expansion_20260910.md`. Its frozen plan
overrides only the initial panel allocation below: ten NEW development and eighty
NEW evaluation packets per corpus, 120 development exposures, 640 core reviews
and combined quality calls, and forty optional reviews. Prompts, schemas, semantic
contract, model digest, decoding, seeds, audit and scoring are identical to v2.
Do not interpret the expansion as changing the historical v2 run.

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

The revised v2 decoding is temperature 0, seed 20260910, num_ctx 32768,
num_predict 8192. Earlier frozen runs retain their original 4096-token setting.
Free-text response fields are bounded to 384 characters. Short exact quotations
are required; input evidence is never shortened. Complete
requests additionally pass a conservative byte-based admission bound including
schema/output reserves. This bound can reject a request that a tokenizer would
fit; it never silently shortens source text or memory. Later oversized learning
requests become visible technical holds without fabricated patches.

The JSON schema is supplied both in Ollama's format field and in the prompt, as
recommended in [Ollama's structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs).
The maximum output allocation is a ceiling, not a target response length. A
length-limited response remains a technical failure, never a usable prediction.

Each reusable rule field is at most 240 characters and their sum at most 640.
Forty active rules and six retrieved rules remain the caps. These are newly
frozen execution limits, not measured optimal settings. Builder candidate_role
is excluded from reviewer input. Original source text, order, source metadata
and legitimate local context are preserved in the restricted task artifacts.

## Identity-bound response protocol

The v2 wire format removes redundant model-authored identifiers and dispositions:

- Detector/reference issue IDs are assigned by array position after parsing.
  Issue text is not changed. This only creates bookkeeping identities.
- Finalizer assessments are required object properties keyed by each candidate
  ID. A retained diagnosis contains refined issue fields without a second ID.
  Discarded/unresolved candidates cannot also appear as retained issues. The
  deterministic adapter constructs the retained list and its established-flaw
  disposition from those explicit decisions. With no retained issues, the model
  chooses no_flaw_established or cannot_judge. Retain means retain the flaw
  allegation, not endorse the source claim.
- Quality allegations and patch-audit edits are keyed by the exact input IDs.
  The adapter converts them to the existing internal records without changing
  true/false/null values, supporting text or audit decisions.
- Learning support IDs are restricted to the available provisional inventory.
  New-rule targets must be empty; replacement targets must be existing non-seed
  rules. Patch IDs are positional bookkeeping, not model-authored rule IDs.
  An empty inventory allows reflection but no supported patch. It is not proof
  that the packet has no flaws. Withholding is not successful adaptation.

The canonical schemas, prompt text and schema-generating implementation are
frozen. Each call journal additionally contains its exact dynamically instantiated
wire schema. Raw wire responses and canonical locked predictions are distinct
artifacts. No after-the-fact ID guessing or semantic correction is performed.

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

A parseable patch audit with absent or incorrect supporting quotes withholds
the update, even if every semantic flag is true. Negative or unknown audit flags
also withhold. They do not trigger a technical retry. The first revised live
preflight exposed that a rejection without quotes had previously raised an
exception; this was corrected before the new experimental run. Original audit
responses remain unchanged. The approval standard was not weakened.

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

## Historical startup classification correction

The first live startup stopped after three development candidate outputs had
contradictory disposition/issue fields. All six reference/detector calls completed;
no Finalizer, learning update or held-out evaluation had run. These complete
but contradictory reviews should reach the already scheduled Finalizer and
quality assessment, not be discarded as unusable transport/schema responses.

The corrected implementation records decision_issue_mismatch as a visible semantic
finding without changing the model's text or decision. Inconsistent references
remain unavailable. A narrowly checked recovery preparation imports every already
completed raw call unchanged into a new versioned run, verifies identical inputs,
prompts/schemas/model/decoding, and preserves the original clock/deadline. It
submits no replacement reference or detector draws for those calls. The original
failed run and its results remain unchanged. This is not a retry-until-favorable
policy or a change to the quality rubric; later semantic errors stay judgeable.

## Authorized v2 restart and launch gate

The recovery1 run subsequently stopped with two length-limited responses and a
Finalizer that discarded an issue while still listing it as retained. On
2026-09-10 the user explicitly instructed testing these errors and starting again.
This authorizes a new, separately frozen v2 experiment, not mutation or resumption
of the terminal run. All scheduled items use the new protocol, not only failures.
No old or smoke-test calls, quality values, references or learned rules are
imported. The original run remains preserved. The new eight-hour budget begins
at the new supervisor launch; preflight time is separate and recorded.

Before restart, run the full offline suite and smoke_ace_flaw_8h.py on the first
two scheduled development packets of every corpus. This includes the three
previously failing packets. Exercise separate combined quality judgments on
development diagnoses only. Test available learning and audit calls without
requiring favorable scores or accepted patches. Zero held-out evaluation packets
may enter this preflight. A false/null judgment, withheld update, or unavailable
reference is not grounds for repeated draws. A technical failure blocks launch.

prepare --restart-from requires a passed smoke_report.json tied to the exact
code, decoding, inputs, model digest and hashed preflight artifacts. It records
restart_provenance.json and imports no experimental outputs. Use a new run path
for every authorized protocol version. Neither these tests nor a successful
launch can guarantee no future model, operating-system or transport failures.
Unknown/failed outcomes remain explicit; no fabricated completion is allowed.

## Same-Protocol Expansion Gate

`prepare --expansion-from COMPLETED_V2 --smoke-report NEW_SMOKE/smoke_report.json`
creates a separate input allocation excluding all completed-v2 packet IDs, text
and source records. It verifies historical manifests, frozen semantic contracts,
prompts, schemas, decoding and model identity. It imports no old outputs or memory.
Counts, schedule bounds, export denominators and the request ceiling come from
the newly frozen plan. This is a new cohort with freshly seeded development, not
a continuation of one learned Playbook or a reason to pool old/new E3 results.

Preparation may precede the smoke test, but supervisor launch cannot. Run
`smoke_ace_flaw_8h.py --source-run NEW_RUN --output NEW_SMOKE` on the first two
scheduled development packets of each corpus. Launch requires eight valid
diagnoses and eight valid quality schemas, zero technical trajectories, matching
development identities, code/model/input/decoding hashes and every artifact hash.
Null/false quality and withheld rules remain acceptable experimental outcomes.
The gate receipt is immutable. Only after this gate passes can the supervisor
start its new eight-hour clock. The original terminal run remains untouched.
