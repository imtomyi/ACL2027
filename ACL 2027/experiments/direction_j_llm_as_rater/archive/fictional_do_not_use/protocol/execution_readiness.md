# Direction J synthetic execution readiness

Status: **not execution-ready**. The checked-in
`config/execution_readiness.template.json` is intentionally incomplete and is
never an approval record. This procedure authorizes only the frozen fictional
qualification lane; it cannot authorize protected real-text access or
processing.

## Required record

Copy the template to restricted, untracked local storage and complete it from
documentary evidence. Do not enter a credential value. The record contains only
the names of environment variables holding the Anthropic and Google credentials;
the checker verifies that those variables are present without printing or
persisting their values.

A passing record must confirm all of the following:

- the exact prepared run, freeze, build report, evaluator bank, fictional-source
  receipt, guide, prompt, shared-rating schema, governance gate, and seven
  assignment hashes;
- the exact non-symlinked provider-neutral renderer and rendering contract plus
  the canonical 96-record packet bank at the fixed project-relative path; every
  packet must remain synthetic-only, contain no provider wire request, authorize
  no network or credential access, and retain wire status
  `pending_provider_profile_and_wire_validation`;
- synthetic-only scope, zero collected ratings or outcomes, an empty raw-response
  area, and a still-blocked real-text gate;
- Charlie's documented first-stage role, qualification, authorization, and
  truthful relationship classification (`independent` or `involved`), plus
  separately documented `QME_QUAL` and `DOMAIN_QUAL` qualifications,
  authorization, and independence declarations;
- a separately hashed human-instrument artifact and readiness receipt confirming
  exact frozen-item/guide semantic rendering, the active timer rule, response
  storage and hash capture, consent/authorization flow, and condition/rating
  blinding; an assignment file is not evidence of instrument readiness;
- account-specific Anthropic and Google processing profiles, including terms,
  retention/deletion, training-use, human-access or abuse-monitoring, routing,
  model-version capture, and disabled tools/external context;
- a real non-symlinked Direction J wire-adapter artifact and request-contract
  artifact for each provider, with exact SHA-256 hashes, a recorded successful
  transport-schema compilation smoke test, and full shared-rating
  post-validation enabled;
- immutable raw request capture before send and raw response capture before
  parsing, per-artifact SHA-256, restricted storage, request/response and model
  identifiers, finish/filter status, usage, timestamps, latency, cost/currency,
  and pricing-snapshot capture;
- a dated approved budget with positive provider allocations and validity through
  the planned Gemini completion; and
- a successful Direction J validator run and a final no-real-text/no-prior-call
  attestation.

Charlie's relationship classification must be supported by a nonblank summary
and documentary reference; the checker does not infer it from an assignment or
role label. `independent` makes Charlie eligible for the primary independence
analysis and does not require separate non-independent reporting. `involved`
does not block synthetic qualification collection, but it makes Charlie
ineligible for the primary independence analysis and requires Charlie's results
to be labeled and reported separately as non-independent. Any inconsistent
classification, eligibility, or reporting combination fails closed.

The Google sensitivity run must be planned, completed, and locked before
`2026-10-16T00:00:00Z`. Run the readiness check immediately before the first
provider call. The record must cite a successful enforcement test showing that
the execution runner independently refuses to start or retain a Gemini call at
or after that deadline; this readiness record is not a waiver or a
silent-model-replacement mechanism.

## Read-only check

From the workspace root, with credential environment variables set only in the
runner environment:

```bash
python3 experiments/direction_j_llm_as_rater/scripts/check_execution_readiness.py \
  --record /restricted/untracked/direction_j_execution_readiness.json
```

The checker reads and validates the record and frozen artifacts, prints a small
text-free pass/reject result, and writes no file. It verifies the renderer and
contract against their freeze pins, executes those already-read renderer bytes
in memory, and requires the checked-in packet bank to match the reconstructed
JSONL byte-for-byte; the packet digest recorded in lineage is the digest of that
verified bank rather than a circular constant in the checker. It rejects the tracked template,
unknown fields or statuses, missing or false prerequisites, missing environment
credentials, mismatched hashes, symlinks, any real-text assertion, nonempty
rating/raw/result state, expired budget, and a Gemini plan at or beyond the
deadline. It also rejects a missing, noncanonical, substituted, or changed
provider-neutral packet bank and any packet that renders or authorizes provider
wire activity. A rejection means stop; there is no override.

Regression checks make no provider calls and create no study records:

```bash
python3 experiments/direction_j_llm_as_rater/scripts/check_execution_readiness.py \
  --self-test
```

A passing readiness check does not execute the study, establish any human role or
qualification, confirm provider facts by itself, or create an empirical result.
Those facts must already exist in the restricted approved record and its cited
evidence.
