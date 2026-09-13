# WarrantRoute ACE-Inspired Static Playbook Experiment

Prepared on 2026-09-09 KST. Status: prepared; inference not started.

## Name and scope

Experiment ID: `warrantroute_ace_playbook_static_20260909`.
The experiment name describes the method. Sample size is a separate setting:
100 packets per dataset, four datasets, three model configurations, one
trajectory per packet/configuration, for 1,200 planned trajectories.

This is the implemented ACE-inspired static Playbook condition. Ten active
method bullets and four dataset adapters are frozen before execution.
The runtime retrieves relevant bullets for each agent call and records their
use. It does not implement ACE's online reflection and persistent Playbook
updates across examples. Renaming the experiment does not add that behavior.
An adaptive ACE condition needs a separate implementation and experiment
contract covering reflection, memory updates, example order and data splits.

## Fixed experimental settings

- Datasets: Dreaddit, GoEmotions, CaChe, ParlaMint-GB.
- Models: Qwen3 8B, Llama 3.1 8B, Gemma 3 4B through local Ollama.
- Each tested model fills all five loop-agent roles in its own condition.
- Role prompts, packet inventory and runtime limits are shared across models.
- One repetition, seed 20260907; at most two revisions and 12 calls per trajectory.
- Playbook updates during evaluation are disabled.
- Existing development packets and historical scoring remain private diagnostics.
- Inputs, model identities, implementation and assets are recorded in manifest.json.
- No paid API calls are configured. Preparation generated no LLM responses.

## Preparation checks

The Playbook validator passed with 10 active bullets and four adapters.
The loop preflight verified the installed model digests and four packet banks.
The existing loop and same-model Table 3 test suites passed: 31 tests.
The current runtime already deduplicates playbook_bullet_ids before schema
validation. This addresses the previously observed duplicate-ID mechanism;
no new live qualification was performed during this preparation.

## Execution

Run from `/Users/tom/Documents/GitHub/ACL2027/ACL 2027`.
The underlying script retains its historical filename for compatibility.

```sh
/opt/anaconda3/bin/python3 -B experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py run --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/warrantroute_ace_playbook_static_20260909
```

The same command resumes the inventory. Existing completed trajectories are
skipped. All technical failures remain in the records and denominator.
For an initial bounded check, append `--max-packets 12` to the run command.

```sh
/opt/anaconda3/bin/python3 -B experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py status --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/warrantroute_ace_playbook_static_20260909
```

After the planned inventory terminates:

```sh
/opt/anaconda3/bin/python3 -B experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py score --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/warrantroute_ace_playbook_static_20260909
```

## Measurement boundary

This bundle prepares the live loop and historical intended-flaw detection
scorer. Credibility/Conformability judging and Table 3 export are not attached
to this bundle. The existing Table 3 supervisor hardcodes the older non-Playbook
configuration, so it must not be used as this condition's launch command.
A separate quality contract must be implemented and frozen before claiming
that this experiment is ready for end-to-end review-quality evaluation.

Human escalation is a terminal loop decision, not independent repair success.
No result, original run, or existing Table 3 value was replaced by preparation.
