# Online v1 Implementation Verification

Date: 2026-09-10. This record describes software verification, not live model
performance or a successfully learned Playbook. The system design follows the
`engineering:system-design` framework: explicit requirements, component/data
flow, contracts and storage, reliability and budget, and documented trade-offs.

## Implemented Artifacts

- [System and experiment design](ace_claim_online_v1.md)
- [Online contracts and memory updates](../../experiments/warrantroute_claim_detection/ace_online_contract.py)
- [Versioned runner](../../experiments/warrantroute_claim_detection/run_ace_flaw_online.py)
- [Online regression tests](../../experiments/warrantroute_claim_detection/test_ace_online.py)

Prepared run, with frozen code, prompts, input inventory and schedule:

`Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_claim_online_v1_dev10_stream80_20260910_prepared`

Status verified through the copied frozen CLI: `prepared_not_started`.
Model requests: **0**. No experiment clock has started. All four current
Playbooks contain only seeds; no new live learning result is claimed.

## Offline Results

From `/Users/tom/Documents/GitHub/ACL2027/ACL 2027`:

```sh
/opt/anaconda3/bin/python3 -B -m unittest discover -s experiments/warrantroute_claim_detection -p 'test_*.py'
```

**123 tests passed**, including 35 new online tests and 88 existing tests.
The final run completed in 7.709 seconds. These use controlled offline fixtures
and mocked transport, never a live LLM. Fixture outputs are not experiment data.

Coverage includes grounded rule addition and next-query retrieval, immutable
seeds, duplicate no-ops, explicit reinforcement, repeated-text support
deduplication across epochs, non-seed refinement, individual invalid/audit-null
edit withholding, memory-budget rollback, and exact quotation validation.

Orchestration checks cover prediction/judgment locking before updates, unavailable
references without suppression of learning, the learning-input allowlist, judge
blinding including error-report side channels, no repeated draw on replay,
recovery after completed stages before item commit, hash/chain tampering,
transport ambiguity, deadline admission, graceful pause, and shared-lock
exclusion before any model contact. Export tests cover four corpora, nullable
quality denominators, finalization, explicit budget-aware retrieval, and an
immutable checkpoint after fifty completed stream items.

## Actual Input Admission

Only frozen inputs were read from the old expansion. Initial detector admission
was checked offline using the new 4096-token output reserve and 32768 context
setting, including the full task, seeds, prompt and JSON schema.

| Dataset | Inputs checked | Maximum conservative bound |
| --- | ---: | ---: |
| Dreaddit | 90 | 18229 |
| GoEmotions | 90 | 15687 |
| CaChe | 90 | 17743 |
| ParlaMint-GB | 90 | 26141 |

The bound combines serialized UTF-8 bytes with the output-token allowance and a
template reserve. It is deliberately conservative, not a measured token count.
All 360 initial detector inputs passed. Dynamic editor, auditor and judge inputs
still require runtime admission and real development-only semantic preflight.

Balance and development/stream separation passed the implemented packet-ID,
normalized-text, record and source-group checks. CaChe retains the previously
authorized within-source exception. Previous diagnostic exposure and constructed
claims remain limitations, not qualifications for manuscript use.

Frozen allocation: 10 development packets per corpus, three development epochs,
80 stream packets per corpus, 120 development exposures, 320 online items,
640 first-pass arm predictions and 640 combined quality-judgment pairs. Maximum
scheduled model calls: 2600. The eight-hour budget is a ceiling, not a measured
completion estimate.

## Preservation and Remaining Gates

The old expansion remains:

`ace_flaw_gemma_expansion_dev10_eval80_20260910`

Its supervisor PID 34077 and worker PID 34087 were observed in OS-stopped states.
All its frozen manifest file hashes still match. Counts remain 120 development
and 515 evaluation results. No old reviewer output, judgment, Playbook, prompt,
clock, historical Table 3, manuscript or automation was modified by this revision.

Before live execution, an explicit user decision is required about the paused
old worker and its still-held shared lock. Real development-only pilot review
of novel lessons, quote grounding, rule use, schema validity and downstream
context admission also remains pending. No claim of improved detection,
Credibility, Conformability, ablation benefit or independent validation follows
from this offline verification.
