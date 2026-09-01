# Dreaddit RQ2 test approval register

Status: **project drafts prepared; external decisions and study-design choices
remain pending**.

## Prepared project-controlled material

| Requirement | Prepared artifact | Current status |
|---|---|---|
| Exact official-test input contract | `DREADDIT_RQ2_TEST_INPUT_CONTRACT.md` | Drafted; approval pending |
| Sampling, packet, and scoring plan | `DREADDIT_RQ2_TEST_PACKET_PLAN.md` | Drafted; sample size, generator, seed, and approval pending |
| Qwen3 Generalist reviewer | `experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_reviewer.py` | Source-free identity and interface checks pass |
| Packet-bank integrity sealer | `experiments/rq2_role_prompted_llm/scripts/seal_qwen3_generalist_packet_bank.py` | Source-free implementation and fail-closed tests complete; no authorized packet bank exists |
| Formal Qwen execution runner | `experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_formal.py` | Source-free implementation and fail-closed tests complete; execution remains blocked |
| Aggregate score exporter | `experiments/rq2_role_prompted_llm/scripts/export_qwen3_generalist_score.py` | Source-free implementation and tests complete |
| External score-promotion gate | `experiments/rq2_role_prompted_llm/scripts/promote_qwen3_generalist_score.py` | Signature verification and tests complete; no trusted authority key, signature, or promotion record exists |
| Source integrity | Dreaddit source manifest and exact-date audit | Hash verified; not use authorization |

## Decisions that code cannot make

| Decision | Required owner or authority | Evidence needed |
|---|---|---|
| Project-specific secondary-use determination | PI and institutional authority | Reference, version, scope, authority ID, effective and review dates |
| Source/platform permission for this Dreaddit copy and intended uses | Authorized source/platform route | Terms or permission reference, scope, authority, dates |
| Exact audit sample size and reserves | Responsible study lead | Signed design decision before test access |
| Independent candidate generator | Responsible study lead and endpoint approver | Actor, immutable snapshot, prompt, role, terms, and separation attestation |
| Qwen local endpoint processing | Institutional/provider or infrastructure authority | `MEP_...` profile covering exact local service and digest |
| Two privacy reviewers | PI or delegated authority | Restricted registry entries, training/access status, and expiry dates |
| Retention, deletion, access logging, and incident response | Data steward or institutional authority | Versioned procedures, deadlines, owner, verification method |
| Aggregate manuscript reporting and any further release | PI, institutional, source/platform, and release reviewers as applicable | Permitted artifact classes, privacy completion, license/attribution decision |

## Required order

1. The PI selects the audit sample size and independent generator, then
   fact-checks the two test-specific drafts.
2. Obtain the institutional and source/platform determinations.
3. Approve the exact generator and Qwen endpoint profiles, access controls,
   retention, deletion, incident response, and aggregate-only release class.
4. Register two authorized privacy reviewers.
5. Create a separate formal local governance record using
   `gate_mode: real_text_candidate`; do not overwrite the personal-only record.
6. Run the project readiness checker. Continue only when Dreaddit reports ten
   completed gates and `real_text_ready: true`.
7. Freeze the official-test selection control, seed, packet rules, actors,
   outcomes, scorer, and analysis before the first test-text access.
8. Select and privacy-review the packets, independently verify one error per
   controlled variant, then seal the evaluator bank and separate truth map.
9. Run Qwen, seal every terminal observation, and create the internal aggregate
   scoring export.
10. A responsible authority signs a promotion record that binds the exact
    aggregate and evidence chain. Verify that detached signature with the
    separately trusted public key. Only the promoted aggregate may replace the
    Table 3 placeholders.

No gate may be marked approved from this register alone. Documentary evidence
and a current machine-validated readiness report remain mandatory.
