# v5 execution readiness

**Design merged; execution not sealed or started.** This list identifies concrete missing work. It is not a request for additional permission to perform already authorized read-only or reversible preparation. The current user pause still prevents launching experiments until the user resumes.

| **Area** | **Status after merge** | **Required evidence before model calls** |
| --- | --- | --- |
| Guideline / metric definitions / tables | Complete as documents | v5 manifest and validation report |
| Model and judge selection | Unselected | Exact model revisions, tokenizer, quantization, role assignments and development-only selection record |
| Server access and allocation | Not currently verified | Authorized connection; current GPU model/count/free memory and owned-process identity; no interference with other lab jobs |
| Runtime reuse | Historical candidate documented | Import/engine compatibility and hashes for the actual selected models on Linux; freeze environment separately |
| 100/100/100 source splits | Not prepared | 1,200 eligible disjoint real records, group/duplicate checks and source/codebook manifests; report shortage rather than inventing records |
| All 28 methods/feedback conditions | Not implemented as a v5 panel | Supervised offline ACE adapters, full optimizer budget mappings and faithful upstream method operations |
| Output schema and probabilities | Not implemented for v5 | Common final labels, explanation, linked quote offsets; independent probability-scoring procedure if used |
| Expanded metric/judge suite | Specified only | Unit/integration checks for formulas, denominator handling, unknown states and corpus-specific profile IDs; calibrated v2 judge |
| Human review | Not annotated | Two reviewers and recorded 20-ID-per-corpus subset; optional completion tracked separately from automated runs |
| Checkpoint and failure behavior | Requires v5 validation | Save prediction before feedback; interrupted update applied exactly once; retry exhaustion/no-op/rejection logs; no old memory import |
| Final auditor | Requires v5 integration | Replay or verify exact source/request/output lineage, immutable predictions, feedback timing, missing records and per-metric denominators |
| GPU service/controller ownership | Historical leases invalid | Fresh allocation and PID/start identity; one worker per cell; explicit service endpoint scope; shared 11434 untouched |
| Launch/monitor | Paused | User resume plus sealed execution manifest and validated new queue; English five-minute reporting |

## Order of preparation

1. Select the backbone/judge on a development-only decision basis. Read the preserved MIATA maps to locate reusable assets; inspect current remote state without launching model calls.
2. Prepare source-disjoint data and codebooks. Compare actual local/remote test IDs before deciding whether the previously used panel can be retained. Record any panel revision.
3. Implement v5 adapters, common schema, metric exporters and seed-aware queue in a new directory. Historical scripts and original manifests remain byte-preserved.
4. Run no-inference validation first: dependency/API checks, data/GT isolation, codebook integrity, output parser and metric formulas, atomic checkpoints, ownership and STOP handling.
5. Run bounded development preflight once execution is authorized. Exercise all adapter paths, malformed/long outputs, memory limits and restart boundaries. Freeze prompt/runtime/source hashes and exact request settings after fixes.
6. Generate the execution manifest enumerating all 84 seed runs per selected model. Verify that no required field is unresolved. Required conditional metrics may be explicitly NC only with the reason; never advertise them as collected.
7. Launch the new owned queue only under the user's resume. Preserve serial adaptation inside each condition. Reference timing uses a dedicated single A6000 and concurrency 1. Additional GPUs require a separately recorded performance profile and actual allocation, not historical service records.
8. Update per-run and shared reports from validated records. Export historical and v5 Notion sections separately when the authorized sync is performed. Stop and preserve state on a later user pause.

## Required execution manifest contents

`protocol_id`, `design_manifest_sha256`, owner, run ID, selected model/judge revisions, all 84 condition-run IDs, dataset/split/order/group hashes, label/codebook versions, source/runtime/dependency hashes, prompts/schemas, decoded generation parameters, probability procedure or NC, judge rubric, optimizer budgets, retry/memory rules, output paths, service identity/allocation, cache policy, audit versions and current launch authorization.

If a manifest setting disagrees with the guideline, stop preparation and record a design revision. An execution seal cannot retrospectively legitimize a method-specific change or inherited result. Successful package-hash validation alone does not validate the experiment implementation.
