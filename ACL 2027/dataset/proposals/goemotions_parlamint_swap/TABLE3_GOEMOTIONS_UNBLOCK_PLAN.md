# Table 3 (GoEmotions) — the real path to genuine numbers

Status: **PLAN. No result exists. Nothing here is manuscript-eligible.**
Date: 2026-08-29 (America/Chicago)

This document turns "fill Table 3 with GoEmotions" into an explicit, ownership-
assigned critical path. It records what was empirically verified, what is
blocked, and the exact decisions that only you (or an independent human, or
governance) can make. No value in Table 3 may be populated except from a frozen,
authorized analysis export produced at the end of this path.

## 1. Empirically confirmed state (from source-free dry-runs, 2026-08-29)

Run against `experiments/rq2_role_prompted_llm/scripts/` (no model contacted):

| Signal | Value | Meaning |
|---|---|---|
| `status` | `passed` | Harness contracts are healthy |
| `manuscript_eligible` | `false` | No output may enter the manuscript |
| `source_bearing_execution_allowed` | `false` | Real (source-text) runs are blocked |
| `routing_policy_bound` | `false` | The WarrantRoute policy is not frozen |
| `heldout_access_allowed` | `false` | No held-out corpus access |
| Qwen3 8B | `primary_source_free_interface` | Interface only, not a bound reviewer |
| Llama 3.1 8B | `adapter_template_unbound` | Not activated; canary required first |
| Gemma 3 4B | `adapter_template_unbound` | Not activated; canary required first |

Conclusion: the machinery exists and its contracts pass, but every gate that
would yield a real, manuscript-eligible number is closed on purpose.

## 2. The six gates to a real Table 3 GoEmotions cell

| # | Gate | Owner | Current status | Can I do it? |
|---|---|---|---|---|
| 1 | GoEmotions download + record-before-analysis | You authorize; I complete | Not started (provenance stub is TODO) | Partly. Download needs your go-ahead; then I complete hashes and field inventory |
| 2 | Freeze the unfrozen router/eval specs | You approve; I draft | Draft proposals in Section 3 | Yes, as proposals for your decision |
| 3 | GoEmotions packet generation + one verified error per variant | I build adapter; independent human verifies | Blocked on gate 2 | I can build the adapter scaffold. The verified-error confirmation is an irreducible human step |
| 4 | Bind all three reviewers (Qwen3 + Llama + Gemma) | You authorize + provide models; I draft configs | Qwen3 interface-only; Llama/Gemma unbound | I can draft freeze configs and canary scaffolds. Activation needs your authorization and the models available locally |
| 5 | Lift the fail-closed `run` gate | Governance / authorized successor freeze | Blocked by design | No. I will not defeat the fail-closed gates |
| 6 | Run, compute clustered bootstrap CIs, freeze export, populate Table 3 | You/governance run; I wire | Blocked on 1 to 5 | Only after 1 to 5 clear |

Nothing downstream can produce a number until gates 1 through 5 are cleared. Two
of those (5, and the human verification in 3) are not mine to clear at all.

## 3. Proposed specs to freeze (your decision: approve or edit)

The README names these as unfrozen and blocking: feature encoding, training
target, model formulation, regularization, expert-time costs and budget,
thresholds, route ties, failure action, development minima, and baseline
procedures. Proposed starting values follow. Each is a proposal for you to fix,
not an authoritative choice.

- **Feature encoding**: the pre-specialist signals only, that is the initial
  researcher rating, recorded uncertainty, and requested-expertise flag. No
  protected attributes, no verified error, no test outcome.
- **Training target**: the route that maximizes detection of the one verified
  error on development packets.
- **Model formulation**: a small interpretable policy over the three signals
  above, consistent with the "interpretable policy" already named in Figure 1.
- **Regularization**: prefer `none` and single-specialist routes over `both`
  unless a signal threshold is met, to bound expert time.
- **Expert-time costs and budget**: fix the per-route expert-minute cost and a
  total development budget before selection. Proposed placeholder to set at
  freeze.
- **Thresholds and route ties**: fix the decision thresholds on development data;
  ties resolve toward the lower-cost route.
- **Failure action**: a failed selected role contributes no flag and is never
  replaced by another role (already implemented in the harness).
- **Development minima**: minimum eligible variants and minimum source clusters
  required before a route is admissible. Proposed placeholder to set at freeze.
- **Baseline procedures**: random routing and uncertainty-only routing, matching
  the RQ1 table already in the manuscript.

Once you fix these, they go into a timestamped preregistration freeze, and the
`routing_policy_bound` gate can be approached through an authorized successor.

## 4. What I will build once you clear the human gates

- After gate 2 approval: the **GoEmotions packet-generation adapter** (corpus to
  theme-and-evidence packets to controlled variants), with the verified-error
  confirmation left as an explicit human-verification step.
- After gate 4 authorization and models available: **Llama 3.1 8B and Gemma 3 4B
  freeze configs and three-role canary scaffolds** (Gemma on the guarded 16,384
  token context path).
- The **run wiring and analysis export** that computes recall and clustered
  bootstrap intervals and writes a frozen export.

## 5. What only you, an independent human, or governance can do

- Authorize the GoEmotions download and the determination that model processing
  and rater exposure are approved.
- Fix and freeze the Section 3 specs in a timestamped preregistration.
- Provide independent human verification of each variant's single verified error.
- Authorize lifting the fail-closed `run` gate through the successor freeze.
- Populate Table 3 from the resulting frozen authorized export.

## 6. Immediate next actions I am asking you to confirm

1. Authorize the **GoEmotions download** (source: Google Research / Hugging Face
   `google-research-datasets/go_emotions`, roughly 58k comments, a few tens of MB)
   so I can complete the record-before-analysis.
2. Approve or edit the **Section 3 specs** so the preregistration can be frozen.

With those two, I will build the packet adapter and model-binding scaffolds. The
run gate, human verification, and governance determination stay with you.
