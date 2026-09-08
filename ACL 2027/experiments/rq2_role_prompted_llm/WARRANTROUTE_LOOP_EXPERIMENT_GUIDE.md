# WarrantRoute Loop Experiment Guide

Date: 2026-09-05

## Prospective Evaluation Addendum (2026-09-07)

For the user's next evaluation design, consult the
[Evidence-grounded evaluation guidelines](../../Storage/experiment_guidelines/objective_review_criteria_v1.md).
They withdraw proposed efficiency-driven input transformations and define
auditable flaw, review-quality and missingness criteria. They also propose a
no-human-reference diagnostic, without changing the user's WarrantRoute code.
No new judge panel or run is authorized by that proposal. Human-panel
recommendations below describe the earlier, distinct research design; they
are not prerequisites imposed on the proposed no-human diagnostic, nor are
they satisfied by replacing humans with model consensus. Existing frozen
experiments retain their original contracts and manuscript restrictions.

## Current Requested Model Comparison

The primary comparison uses one LLM throughout each loop: `qwen_only`,
`llama_only`, and `gemma_only`. Proposer, Evidence Scout, Methods Challenger,
Domain Challenger, Reviser and every recheck use the condition's fixed model.
The main launcher now defaults to the
[same-model configuration](config/warrantroute_loop_n100_same_model_v1.json).
No mixed-model fallback is allowed. The internal policy ID
`same_model_ablation` is retained for compatibility, but this is now the
requested primary comparison rather than an optional ablation.

The prepared primary bundle is
[`n100_same_model_ready_20260905/manifest.json`](../../Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_ready_20260905/manifest.json).
It contains the four datasets at 100 packets each and all three single-model
conditions: 1,200 trajectories. Preparation made no generation requests.
Use `run` on this existing bundle, not `prepare` again. It includes no external
quality judge or automatic Table 3 export.

The [same-model protocol](protocol/warrantroute_same_model_quality_v1.md) and
[`run_warrantroute_same_model_table3.py`](scripts/run_warrantroute_same_model_table3.py)
add a separate secondary Credibility/Conformability audit and Storage-table
export. The basic launcher does not invoke that judge or change Table 3.
External grading must use the same procedure across all three conditions;
changing the grader with the tested model would also change the measurement.
The optional fixed Qwen judge has a disclosed self-family preference risk.

The old `n100_ready_20260905_v2` preparation predates this opt-in implementation
and is a historical unlaunched bundle, not the current launch target. Its hashes
are intentionally not rewritten. Prepare a new run to use changed source code.
The same-model supervisor provides `prepare`, `run` and `status`, each with a
required `--run-dir` under the existing live-loop Storage directory. It freezes
loop and judge contracts before inference, runs and scores the loop, judges
original-review projections, and updates only the Storage Table 3 WarrantRoute
rows after completion. No manuscript files are modified.

This guide identifies the existing implementations and defines the executable
n=100 private working experiment. The public method name is **WarrantRoute**.
The primary implementation ID is `live_evidence_revision_loop_same_model_v1`.

## 1. Start here

The live experiment entry point is
[`scripts/run_warrantroute_loop_n100.py`](scripts/run_warrantroute_loop_n100.py).
Its per-packet implementation is
[`scripts/warrantroute_loop_runtime.py`](scripts/warrantroute_loop_runtime.py).
Model assignments, packet locations and budgets are in
[`config/warrantroute_loop_n100_same_model_v1.json`](config/warrantroute_loop_n100_same_model_v1.json).
English agent instructions are in
[`prompts/warrantroute_loop_v1.md`](prompts/warrantroute_loop_v1.md).

The ACE-inspired static Playbook pilot uses
[`config/warrantroute_loop_n100_same_model_playbook_v1.json`](config/warrantroute_loop_n100_same_model_playbook_v1.json)
and [`prompts/warrantroute_loop_v2_playbook.md`](prompts/warrantroute_loop_v2_playbook.md).
Its Playbook is frozen in
[`playbooks/warrantroute_method_playbook_v1.json`](playbooks/warrantroute_method_playbook_v1.json)
with dataset adapters under [`playbooks/dataset_adapters/`](playbooks/dataset_adapters/).
Validate it before launch with
[`scripts/validate_warrantroute_playbook.py`](scripts/validate_warrantroute_playbook.py).
The implementation records supplied and used `playbook_bullet_ids`, but keeps
Playbook updates disabled during evaluation.

The runner provides `preflight`, `prepare`, `run`, `status`, and `score` commands.
Preparation creates a fixed packet snapshot and run manifest. Only `run`
dispatches LLM calls. `score` reads the answer sheet after the full planned
inventory has finished. A prepared run resumes with the same `run` command.

The original mixed-family prepared bundle was `n100_ready_20260905_v2`. See the
[readiness record](../../Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/READINESS_20260905.md)
for its manifest, verified tests, live qualification outcomes and superseded
preparations. That mixed-family inventory was not launched.

The four existing working banks each contain 100 selected packets: Dreaddit,
GoEmotions, CaChe and ParlaMint-GB. These have already been exposed during
development. Their source-derived claims include controlled flaw templates.
Use their results for engineering and model-configuration screening. They are
not fresh held-out observations or manuscript evidence.

## 2. Implementation audit

| Component | Actual behavior | Execution status |
| --- | --- | --- |
| `run_working_generalist_reviews.py` | Live Ollama calls under Generalist, Methods and Domain prompts; despite its filename, supports all three roles | Existing working acquisition runner; no revision loop |
| `build_working_warrantgate_routes.py` | One cost-sensitive route decision from a Generalist projection | Existing static routing tool |
| `build_working_warrantgate_adaptive_routes.py` | Segment-level route scoring and packet-level role union | Existing working adaptive routing tool |
| `run_working_warrantloop.py` | Fits model-specific logistic gain/harm estimators and simulates sequential specialist acquisition | Runnable cached-output development replay; no new LLM calls |
| `run_working_warrantloop_multicorpus.py` | Dreaddit out-of-fold replay and transfer to the other three datasets | Runnable cached-output comparison across Qwen, Llama and Gemma |
| `run_working_warrantroute_cascade.py` | Retains Generalist flags while replaying fixed routes | Runnable output-composition experiment; no revision or new LLM call |
| `run_working_warrantroute_residual.py` | Adds predictions from a hashed Naive Bayes residual detector | Working diagnostic; known template shortcuts invalidate superiority claims |
| `run_qwen3_warrantroute.py` | Formal source-free contracts and reduction | Policy inference and real execution are deliberately unavailable |
| `run_warrantroute_multimodel.py` | Formal profile validation and deterministic reduction | `train` and `run` are blocked; the local Qwen dry-run also reports `required_file_unavailable` in this checkout |
| `ace_tight_loop_controller.py` in Direction H | Accept/revise/escalate decision over supplied state | A controller, not an LLM transport; used by the new runtime |
| `run_warrantroute_loop_n100.py` | Live agents, routed audits, bounded revision, rechecks, resumable records and comparison export | New private n=100 runner |

The separate `ace_paper/` directory reproduces ACE on its original benchmark
tasks. Its Finance/AppWorld commands do not run WarrantRoute or biomedical
thematic analysis.

The older cached replay and the new revision loop are different experimental
conditions. In particular, the old Generalist path costs one reviewer call;
the new loop always begins with two independent assessments.

The old model-specific trained routing coefficients and thresholds are stored
in the [calibrated transfer policy](../../Storage/rq2_personal_local_diagnostic/warrantloop_working/multicorpus_n100_20260902_calibrated_cascade_breakpoints_v2/policies/dreaddit_transfer_policy.json).
Its `model_policies` contains separate `final_transition_models` and
`selected_threshold` entries for all three LLMs. These numeric routing models
are distinct from the Ollama language-model weights and from the new live
loop's initial WarrantGate policy.

## 3. Which LLMs to use

Use the installed local Ollama models `qwen3:8b`, `llama3.1:8b`, and `gemma3:4b`.
Their exact model digests are recorded in the configuration and checked against
the running local service during preparation and execution. All three current
snapshots report Q4_K_M quantization. These are role-prompted models; this
experiment does not fine-tune their weights or establish biomedical expertise.

The primary conditions hold the model fixed across every role:

| Condition | All initial agents, revision and rechecks |
| --- | --- |
| `qwen_only` | Qwen3 8B |
| `llama_only` | Llama 3.1 8B |
| `gemma_only` | Gemma 3 4B |

Use the same packet IDs, role prompts, routing weights, generation budgets,
stopping rules and seed schedule in all three conditions. Routes and the
number of calls may differ because the models produce different assessments;
that is an outcome to measure, not a reason to force identical trajectories.
Compare original-flaw detection, independently evaluated quality, failures,
tokens and elapsed time. Gemma has a different parameter count, so this is a
comparison of these installed model configurations, not model family alone.

The following mixed-family assignments are retained only for an explicitly
requested allocation/diversity experiment. Select them with
`--config experiments/rq2_role_prompted_llm/config/warrantroute_loop_n100_v1.json`
during preparation. They are not the default model comparison:

| Agent | qwen_led | llama_led | gemma_led |
| --- | --- | --- | --- |
| Proposer | Qwen3 8B | Llama 3.1 8B | Gemma 3 4B |
| Evidence Scout | Gemma 3 4B | Qwen3 8B | Llama 3.1 8B |
| Methods Challenger | Llama 3.1 8B | Gemma 3 4B | Qwen3 8B |
| Domain Challenger | Gemma 3 4B | Qwen3 8B | Llama 3.1 8B |
| Reviser | Llama 3.1 8B | Gemma 3 4B | Qwen3 8B |

Every mixed-family assignment separates the Proposer and Reviser model families and includes
an auditor from a different family. Each model occupies each role once across
the three configurations. Agents are separate calls even when two roles use
the same model. Role independence is not a guarantee of independent errors.

These mixed assignments are **system-configuration comparisons**. A qwen_led
result reflects three model families, so do not label it simply "Qwen accuracy".
The primary `*_only` conditions instead hold model identity fixed while keeping
agent roles separate. Separate same-model calls do not guarantee independent
errors. The default controller safeguard for configs without an explicit
assignment policy remains cross-family separation.

## 4. Exactly what the live loop does

The n=100 profile reviews the supplied claim. It does not replace that claim
before measuring original-flaw detection.

1. Lock the original claim and provide an allowlisted task payload. Remove
   hidden flaw fields, generation-model identity and arbitrary source metadata.
2. Run Proposer and Evidence Scout independently. The local scheduler executes
   them serially, with no exchange of their initial outputs.
3. Apply the existing WarrantGate v0 scores to the Proposer rating and packet
   structure. Use a fixed numerical tie tolerance. Honor explicit requests for
   additional specialist expertise from the initial audits.
4. Run the selected Methods and Domain challengers. Their requests can expand
   the visited role set, including M to B or D to B. The four terminal modes
   remain Generalist, Methods, Domain and Both.
5. Record evidence-linked material issues. Derive flag lists from those issues
   in code. Freeze the detected flags for the original candidate.
6. If needed and budget permits, the Reviser addresses every open issue ID.
   Only the Evidence Scout and original issue owners recheck the new candidate.
   The Reviser cannot mark its own repairs as resolved.
7. Stop after acceptance, unresolved abstention, exhausted budget, or at most
   two revision rounds. A request for a previously inactive specialist after
   revision is escalated to human review in this version.

The new runner uses **WarrantGate v0 plus explicit expertise escalation** for
initial routing. It does not silently reuse logistic policies fitted to old
prompts as if they were calibrated for the new agents. The learned expected-
gain policies remain in `run_working_warrantloop.py` and require a separate
calibration experiment for this new observation space.

The controller's acceptance decision means that the executed checks and audits
have no remaining blocking issue. It is not an expert reference label. Schema,
ID, model-identity and issue-ownership checks are structural checks. Whether a
paraphrase is faithful or an interpretation is clinically warranted still
requires semantic evaluation.

Playbook updates are disabled during this n=100 evaluation. The outer Failure
Reflector, Counterexample Reflector and Memory Steward remain a development
extension. Their outputs must not alter the system between test packets.

## 5. Commands

Use the tested Python environment from the project directory:

```sh
cd "/Users/tom/Documents/GitHub/ACL2027/ACL 2027"
```

Check the packet inventory and installed model identities without generation:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  preflight --configurations all
```

Prepare all four n=100 datasets and all three assignments:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  prepare --configurations all \
  --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_ready_20260905
```

Once that directory exists, launch or resume it with:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  run --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_ready_20260905
```

Add `--max-packets 3` to process at most three additional trajectories and return.
Completed trajectories are skipped on resume. A failed or interrupted call is
retained and is not automatically retried under a new identity. Start a new
diagnostic run to test a changed prompt, model or failure policy.

Inspect progress and score the complete inventory:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  status --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_ready_20260905
```

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  score --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_ready_20260905
```

For a smaller new plan, `prepare --datasets dreaddit --configurations qwen_only`
uses only Dreaddit. `--sample-n 1` selects one development packet for an
engineering check. The source bank must still contain the expected 100 records.
Selection uses fixed packet-ID order, not answer labels.

## 6. Size and budget

| Plan | Trajectories | Maximum agent calls |
| --- | ---: | ---: |
| One dataset, one assignment, one repetition | 100 | 1,200 |
| Four datasets, one assignment, one repetition | 400 | 4,800 |
| Four datasets, three assignments, one repetition | 1,200 | 14,400 |
| Four datasets, three assignments, three repetitions | 3,600 | 43,200 |

A trajectory is one packet under one assignment, method and repetition.
The maximum is a cap, not a prediction. Each trajectory begins with two calls.
The optional `always_on` and `no_revision` conditions add separate trajectories.
Use `--repetitions 3` during preparation for seeds 20260905, 20260906 and 20260907.
Do not count repetitions as independent source samples.

Current settings are temperature 0.2, top_p 1, context 16,384, a 1,024-token
audit cap and 2,048-token revision cap, a 240-second request timeout, at most 12 calls and
two revision rounds. Qwen thinking is disabled explicitly. Seeds are derived
from the repetition, role and stage and are identical across configurations for
the same role/stage. Exact cross-model outputs are not expected to match.

The token cap is larger than the provisional short-output budgets in the design
note because this executable profile returns complete structured ratings and
located issues. Qualification should assess truncation and schema failure
before reducing it. The input character screen is a coarse guard, not an exact
cross-tokenizer context-length proof.

## 7. Comparison protocol

First compare the three single-model conditions on the same 100 packets per dataset.
Report every condition, including failures. Do not choose the best test result
and then relabel it as a preregistered primary model.

For mechanism comparisons, prepare a separate plan with:

```text
--methods warrantroute always_on no_revision
```

- `warrantroute`: conditional specialist audits and bounded revision.
- `always_on`: all initial agents and the same revision/recheck rules. This is
  the matched comparator for the cost of routing.
- `no_revision`: identical routed initial audits with revision disabled. Compare
  independently rated repair quality to measure revision benefit. Original-
  claim recall should not improve merely because a later candidate was edited.

Historical Table 3 All roles unions three reviewer outputs. The new always_on
condition contains four initial agents including Evidence Scout. Give them
different labels. Report historical comparisons separately unless all inputs,
prompts, model snapshots and measurement procedures are matched prospectively.

For a stronger later model-allocation study, evaluate all six permutations of
the three model families across Proposer, Reviser and Evidence Scout, using a
declared fixed mapping from those assignments to Methods and Domain roles.
Select the final configuration on development data under a prespecified time
or token budget. Freeze it before using new source-disjoint test material.

## 8. What to measure

The implemented scorer reports original intended-flaw recall, connected source-
component bootstrap intervals, paired recall differences between conditions,
calls, input/output tokens, wall time, revision rounds, acceptance frequency,
and error frequency. It uses 10,000 cluster resamples with seed 20270826. A
single source component cannot supply a meaningful cluster interval.

These intervals are exploratory, unadjusted for multiple comparisons, and
conditional on each repetition. The independent sample size is the number of
source components, not model calls or repetitions. A later confirmatory
analysis needs a declared primary contrast and multiplicity plan.

The current answer sheet identifies intended flaws. It does not establish
that every unlisted flag is false or provide a unique correct rewrite. Do not
derive precision, false-positive rate or repair success from it. Those require
independently reviewed negatives, complete flaw annotations, or expert review.

For biomedical thematic analysis, independently judge the original and revised
claims with model/condition labels hidden and presentation order randomized.
Use evidential credibility, voice-and-boundary preservation and scope
calibration as separate constructs. Also record newly introduced material
errors and the rate at which acceptable originals are made worse. Keep
`repair_quality` empty until that evaluation is available.

The legacy queue's optional quality judge defaults to Qwen3 8B. It is not the
final grader for this new experiment. For the principal biomedical comparison,
use an independent qualified human panel. Any LLM judge should be a separately
frozen secondary measurement with a human-audited subset, especially when the
same model family participates in the loop.

Select a configuration on the quality-cost frontier. For example, minimize
measured wall time subject to a development-set quality target and a limit on
harmful revisions. Choose those targets before final-test access. Calling
every agent less often does not by itself establish better quality.

## 9. Cost accounting and records

Each call record preserves model digest, role, stage, seed, request hash, raw
output, parsed output, completion status and returned usage. The API reports
input/output token counts, generation time and model-load time; these are
recorded separately. See the official [Ollama generation API](https://docs.ollama.com/api/generate).
Exact snapshots are obtained from the [model inventory API](https://docs.ollama.com/api/tags).

The runtime uses JSON-schema constrained output and validates the returned
object again. JSON validity does not establish interpretive correctness. See
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

Resume reuses a call only when its complete request and model digest match.
Unknown usage after a timeout remains marked incomplete. A packet can retain
valid original detections from earlier calls even if a later revision fails;
the failure remains visible and the packet stays in the denominator.

Cached replay counts are hypothetical selected-call counts. The new runtime's
wall time is measured live and includes model loading. Local execution has no
per-token API invoice, but compute and operator time are not zero. Freeze the
hardware, scheduler, warm/cold loading procedure and model order for latency
comparisons. Tokens from different tokenizers are not equal units of compute.

The output directory contains `manifest.json`, fixed inputs, source-code snapshots and assets,
per-packet `calls/` and `result.json`, `progress.json`, and after scoring,
`comparison.md`, `comparison.csv`, `comparison.json` and private scoring detail.
No result is written into the manuscript by this runner.

## 10. Readiness and scope

The new code implements the inner live loop. The existing Direction H design
and controller alone did not previously make it executable. This distinction
corrects the earlier description of what had already been connected.

Current working execution does not implement learned revision-value estimation,
automatic Playbook learning, an independent repair-quality judge, or a formal
publication pipeline. The older formal `run` and `formal-run` entry points
retain their existing blocked behavior. Use this new entry point for the
prepared private n=100 experiment, not as a way to mark historical data as a
fresh test set or populate manuscript result cells.
