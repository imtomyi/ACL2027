# CaChe and ParlaMint-GB: paired reference-feedback pilot

This exploratory run uses real source excerpts and unverified, locally generated reference annotations. It is stored separately from the manuscript and the original GT-free run. No human-GT benchmark result or exact reproduction of the finance-paper experiments is claimed.

## Conditions and table note

**GT ✓†:** a frozen Qwen3-8B annotation is supplied as fallible feedback during adaptation. These are model-generated pseudo-labels, not human ground truth. **GT ✗:** no reference annotation is supplied during adaptation. Base uses neither. The dagger must accompany every ✓ for these two corpora.

Each corpus has seven rows: Base; ACE offline ✗ and ✓†; DC online ✗ and ✓†; ACE online ✗ and ✓†. ICL, MIPROv2 and GEPA are not included in this pilot. The existing GoEmotions experiment remains separate and paused while this run uses the local model.

## Data and task

The fixed selection contains 100 adaptation and 200 evaluation excerpts per corpus. This is a pilot, not the entire corpus. It copies the previous GT-free selection exactly. Source sessions are disjoint across adaptation and evaluation. Speakers can recur across ParlaMint sessions. See the data manifests for provenance, filtering, reservoir seed and file hashes.

The task selects all explicitly supported topics from a fixed provisional corpus-specific codebook and explains them using exact source quotations. These codebooks are not the official CAP taxonomy. All conditions return the same structured topic IDs plus explanation. Because this adds a structured field, the earlier 28 CaChe Base outputs are preserved separately and not mixed into this comparison.

## Reference generation and feedback timing

The same local Qwen3-8B model generates all 600 reference annotations from source text and codebook only. It does not see evaluated answers, method names, playbooks or judge outcomes. It uses temperature 0, seed 42, thinking disabled and a 1,024-token output cap. Up to three technical attempts are allowed for invalid schema, IDs or quotations. Label correctness is not used to select retries. Exact-quotation checks establish traceability, not semantic correctness. A hashed annotation manifest is sealed before comparative prediction.

Offline ACE uses feedback only on the 100 adaptation excerpts, then freezes its playbook for evaluation. Online ACE and DC generate the current prediction before that example's reference feedback can update memory for subsequent examples. Online performance is pre-update performance. The orchestration layer may load a DC reference in advance, but injects it only into the curator call. Generator and Conformability judge calls never receive that reference. DC format repair does not receive additional reference feedback.

## Implementation and budgets

ACE uses the vendored official generator, reflector and curator templates, bullet counters and ADD operations, in a durable local serial loop. Each adaptation item has one generation, one reflection and one curation. It uses one epoch, with no deduplication analyzer or validation-based selection. With-reference and without-reference conditions use the corresponding official template variants. Their caps are identical: 1,024 generator, 1,536 reflector and 2,048 curator output tokens, and an 8,000-token playbook cap. Invalid or oversized ACE updates retain prior memory.

DC uses the vendored cumulative workflow and local adapter, one round, with code execution disabled. The generator has a 2,048-token output cap; the official cumulative workflow doubles that cap to 4,096 for the curator and its format repairs. At most two format-only repair calls are allowed; unrecoverable formatting retains previous memory with an audit record. DC memory is constrained by the shared context guard, rather than the ACE 8,000-token playbook cap. All methods share the 32,768-token context guard and reject detected truncation. Different prompt lengths and responses can produce different actual costs despite identical paired caps.

All generation, annotation and judgment are local. Frozen source hashes and an implementation snapshot are saved alongside the run. Per-call caches and atomic checkpoints support interrupted-run recovery. Software tests cover reference validity, duplicate IDs, feedback routing, official ACE template formatting, offline test-label isolation and online prediction-before-feedback order. Test fixtures do not contribute to experiment results.

## Metrics and interpretation

Human-GT Acc and F1 remain N/A. **Reference agreement** is exact topic-set agreement with the frozen model annotation, divided by all 200 evaluation items; invalid model outputs count as nonagreement. It is not accuracy against independent ground truth. It intentionally measures alignment with a reference that the ✓† condition learns from, so it must not be interpreted as an independent measure of improvement in correctness.

**Conformability** is the existing source-grounding rubric evaluated by the same local model family, blind to reference annotations and method identity. Judge outcomes never feed adaptation. A final percentage requires all 200 judgments and zero unresolved judgments. Partial counts, failures and unresolved cases remain visible. The same-family teacher, generator and judge can share errors; neither metric establishes human-validated correctness.

RESULTS.md links to METRICS.md. Both are updated from actual checkpoints. These exploratory artifacts are not used to fill manuscript result placeholders.
