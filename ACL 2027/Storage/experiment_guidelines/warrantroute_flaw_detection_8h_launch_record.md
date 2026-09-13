# Eight-Hour ACE-Inspired Flaw-Detection Launch

Date: 2026-09-10 KST. User request: start the experiment and produce an ACE method
results table for all four datasets and Playbook results.

## Active run

The user requested more data under the same experiment on 2026-09-10. The
same-protocol expansion was temporarily paused at the user's request on
2026-09-10 at 10:06:17 KST, after the in-flight job and its quality judgment
and progress export completed. See
[allocation and withholding analysis](ace_flaw_expansion_20260910.md).

Pause status: 515/640 core reviews and quality judgments are technically valid,
with 194 both-binary quality pairs, 120/120 valid development exposures and zero
technical trajectories. No unanswered model requests remain. Worker 34087 and
supervisor 34077 are OS-suspended, retaining their state and locks. The progress
automation is PAUSED. No active completion ETA applies while paused. See the
active directory's `pause_record.json`; saved `status.json` retains its last
running snapshot. No frozen artifact or original deadline was changed. Resume
requires a new user request and checks of process identities, integrity and the
original remaining budget. Do not automatically resume after the deadline.

- Directory: `Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910`.
- Screen: `ace_flaw_expansion_dev10_eval80`.
- Start: 2026-09-10 06:26:16 KST. Immutable hard deadline: 2026-09-10 14:26:16 KST.
- Supervisor PID at launch: 34077. Worker PID: 34087. One worker only.
- Same local Gemma 3 4B, v2 prompts, schemas, semantic-contract byte hash, decoding, seed rules, audit and scoring.
- Each of four corpora: ten NEW development and eighty NEW evaluation packets.
- New unique packets: 360. Development: 120 exposures. Core: 640 matched E0/adapted reviews and combined judgments. Optional: forty checkpoint reviews.
- New references, reviews, judging and development memory only. No imports from previous runs or smoke tests. Historical outputs are preserved and not pooled.
- Offline suite: 88 tests passed, including a complete mocked expanded schedule, denominator checks, exclusion checks and missing-preflight launch rejection.
- Initial admission checks: all 720 reference/detector requests fit the conservative context bound; maximum 27,509 against 32,768. Later memory-dependent requests remain subject to their own admission checks.
- Exact-text, packet-ID and source-record overlap with completed v2: zero in all corpora. Additional read-only NFKC/casefold/whitespace-normalized text checks also found zero old/new and new development/evaluation overlap. CaChe retains the authorized within-source split.
- Live preflight: `Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_expansion_smoke_20260910/smoke_report.json`.
- Preflight ran 06:20:48-06:25:54 KST: eight development-only diagnoses, eight technically valid combined judgments, 42 completed local calls, zero technical trajectories and zero evaluation packets. All input/code/model/decoding/artifact hashes passed the launch gate.
- Preflight accepted zero learned rules. Null judgments, unavailable references and rejected updates were preserved and did not trigger retries. Passing this gate establishes executable contracts, not successful learning or scientific validity.
- Initial workload ETA: about six hours using completed-v2 per-role upper-quartile timings and the new maximum call allocation. Recompute from actual new observations as available; do not confuse proxy-based initial status estimates with observed throughput. Eight hours is a hard budget, not a completion guarantee.
- Five-minute automation `warrantroute-ace-ta-progress` was ACTIVE as `ACE flaw detection expansion progress`, targeting only this expansion. It is now PAUSED with the user-requested experiment pause. Its saved monitoring instructions are unchanged. Do not archive the task.
- Results remain private, manuscript-ineligible diagnostics. No paid API calls. No historical Table 3 update.

The active run's `results_table_ACE.csv/.md` has four corpus rows with Planned_N
80. `playbook_result.csv/.md` reports actual rule creation, withholding, support
and retrieval. `dataset_quality.csv` retains E0/adapted rows; paired-change and
fixed-probe exports remain separate. Do not replace a null with true to fill a
cell, or treat seed-only memory as demonstrated adaptation.

## Completed V2 Run

Project-relative directory:
`Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_8h_gemma_20260910_v2`.

- Screen: `ace_flaw_8h_gemma_20260910_v2`.
- Model: local `gemma3:4b`, digest frozen in manifest.json.
- Method display: ACE-inspired WarrantRoute-Lite, not original ACE replication.
- Scope: Dreaddit, GoEmotions, CaChe, ParlaMint-GB; each ten development and twenty
  evaluation packets. Three epochs, matched seed/adapted quality, optional probes.
- New authorized start: 2026-09-10 01:32:50 KST.
- New run's immutable eight-hour deadline: 2026-09-10 09:32:50 KST.
- Supervisor PID at launch: 13095. Worker PID at launch: 13105.
- Local-only inference; zero paid API authorization or usage.
- End: 2026-09-10 03:36:15 KST, `completed_with_unresolved_quality`.
- Actual counts: 120 valid development exposures, 160 valid core reviews and
  quality schemas, 64 both-binary pairs, forty optional reviews, zero technical
  trajectories. Ninety-six core reviews had at least one null quality dimension.
- Four seed-only Playbooks, no accepted new rules. This run is terminal and must
  not be resumed. Its progress automation was paused on completion and later
  retargeted to the separate expansion above.

## V2 preflight and restart

After recovery1 stopped, the user explicitly instructed testing the errors and
starting again. V2 is a new experiment under revised frozen transport/prompt
contracts, not a continuation that selectively replaces failed outcomes.

- Full offline suite: 81 tests passed. Tests cover all 27 three-candidate
  disposition combinations, audit refusal/unknown/missing evidence, immutable
  outputs, no retry after ambiguous or length-limited calls, matched quality,
  identity-bound responses, seed protection, and a complete mocked schedule.
- Passed live preflight:
  `../rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_v2_smoke_20260910_0128/smoke_report.json`.
  It used two scheduled development packets per corpus, including all three
  previously failing packets: eight valid diagnoses and eight valid quality
  responses, 46 completed local model calls, zero technical trajectory failures,
  and zero held-out evaluation packets. False/null values did not affect passage.
- All 240 initial reference/detector request sizes for the 120 distinct selected
  packets fit the conservative context bound. Later memory-dependent calls still
  have admission checks; this is not a guarantee against every future failure.
- The first revised preflight, ending `_0124`, found the audit-rejection error.
  Its original responses and failure record remain separate and unchanged.
- No new Playbook rules were accepted in preflight. Most proposed edits copied
  existing seed rules and were withheld. This is a learning concern, not a
  successful-adaptation claim or a reason to fabricate rules. Track actual rule
  creation, support, audits, and evaluation retrieval in the new run.
- V2 binds identifiers to input objects, bounds free text, explicitly distinguishes
  retaining a flaw from endorsing a claim, and restricts add/replace targets.
  Unsupported or rejected audits withhold memory rather than raise a technical
  exception. Approval still requires exact support and all six true criteria.
- Temperature remains 0, seed 20260910 and context 32768. The output ceiling is
  8192 tokens, with bounded fields to prevent runaway repeated prose.
- Preparation verified the exact code, model digest, inputs, decoding and all
  hashed smoke artifacts. `restart_provenance.json` records the authorization.
  Every scheduled packet uses v2; no old or preflight calls, references, quality
  values, or learned memories are imported. Original failed runs are preserved.

The new clock begins at the new supervisor launch. Earlier failed-run and
preflight time are separate overhead, not silently relabeled as this run's time.
These checks validate software execution, not scientific accuracy or improvement.

## Requested outputs

Within either run's own directory, without combining their results:

- `results_table_ACE.csv` / `.md`: four dataset rows for adapted Credibility and
  Conformability with actual counts, coverage and explicit missingness.
- `playbook_result.csv` / `.md`: generated rules, accepted/withheld updates,
  evidence support, audit and evaluation-retrieval status per corpus.
- `dataset_quality.csv`: seed and adapted quality rows.
- `paired_changes.csv`: same-packet jointly resolved quality changes.
- `fixed_probe_curve.csv`: common five-packet checkpoint diagnostics.
- `playbooks/<dataset>/current.json/.md`, epoch snapshots and update diffs.

Percentages appear only from actual judgments. Pending cells are not filled
with simulated values. These constructed-claim, same-model diagnostic outputs
remain under Storage and cannot enter the manuscript or historical Table 3.

## Historical startup incidents and preservation

The original directory ending `_005222` stopped after three development reviews
were wrongly rejected before the scheduled Finalizer for a disposition/issue
contradiction. All six initial reference/detector calls had completed. No complete
diagnosis, learned update or held-out judgment existed at that point.

The corrected classifier preserved contradictory text as a semantic finding for
the Finalizer/judge. Historical recovery1 imported all six completed raw calls with
identical hashes, identical prompts/schemas, inputs, model and decoding. Those
reference/detector draws are NOT repeated. Original failures remain in the old
directory. The original eight-hour clock is preserved rather than restarted.
Its `recovery_provenance.json` records the narrowly checked import and hashes.
Recovery1 later stopped at 2026-09-10 00:59:42 KST after six development exposures
(three valid). Two responses reached the old 4096-token limit, and one Finalizer
discarded a flaw while still listing it as retained. No held-out evaluation or
quality judgment was completed. Both failed directories remain terminal.

At that historical launch, sixty-six offline tests passed, including a complete mocked schedule and tests
for contradictory-candidate handling. These are engineering checks, not results.
Post-launch checks confirmed matching frozen-file hashes, matching imported-call
hashes, preserved deadline, and new scheduled Finalizer calls completing without
the original classification failure. Learning holds and unavailable references
remain visible; no performance or Playbook-success claim is made at launch.
