# Historical evidence and reuse map

## Separate experiment scopes

| **Scope** | **Recorded completion** | **Recorded failure / pending** | **Interpretation** |
| --- | --- | --- | --- |
| Local run_20260914_uniform | 10/24 conditions | 2 failed; 1 paused mid-run; 11 queued | Qwen3-8B local comparison; 100 evaluation items each; existing results stay in original directories |
| MIATA original matrix | 27/30 conditions | 3 failed DC conditions | Mixed historical task sizes and ACE recovery versions; saved handoff claim, not a fresh remote audit |
| MIATA DC curator-8192 | 2/8 conditions | 2 failed; 4 unstarted | Separate executions, excluded from original completion numerator |
| v5 new server panel | 0/28 conditions; 0/84 seed runs | Not started; configuration and implementation incomplete | This package contains design and historical evidence, no v5 scores |

The local pause checkpoint recorded GoEmotions DC GT✓ at 86 saved predictions, 85 completed updates and 0 judgments. MIATA has a different execution history; never replace one count with the other. Inspect live state before any later resume.

All 12 selected MIATA ACE conditions are reported complete. Original failed DC conditions are Dreaddit with reference feedback and GoEmotions with/without reference feedback. The selected old result table is preserved exactly in [RESULT_MATRIX.md](sources/miata_handoff/RESULT_MATRIX.md); exact metadata and receipt mapping remain in [RESULT_AND_PENDING_INVENTORY.json](sources/miata_handoff/Storage/inventories/RESULT_AND_PENDING_INVENTORY.json). Do not retype or infer missing scores.

## MIATA assets

All paths below are under `/home/sy23985/Storage/` on MIATA, based on the saved inventory. These are not verified current mounts.

| **Root** | **Use** | **v5 handling** |
| --- | --- | --- |
| acl2027_miata_resume_20260913 | Original migration, Linux runtime, Qwen model/tokenizer and source/data snapshots | Reuse compatible assets after current integrity checks; do not overwrite pins |
| acl2027_ace_pending_20260913 | ACE Original/V2/V3/V4 results and audits | Historical evidence; candidate method source for reviewed adapters |
| acl2027_comparison_completion_20260913 | Comparison data, physical-call journals, receipts and stop records | Input provenance and audit architecture; no score imports |
| acl2027_dc_curator8192_20260913 | Larger-cap DC outcomes and failure proofs | Failure regression evidence; no automatic prefix continuation |

Shared interpreter: `acl2027_miata_resume_20260913/runtime/venv/bin/python`, recorded Python 3.13.2. Ollama binary: `runtime/ollama_distribution/bin/ollama`, recorded 0.33.3. Existing weights: `runtime/ollama_models/`. The historical Qwen3-8B digest and tokenizer pins are in [RUNTIME_PINS.json](sources/miata_handoff/Storage/inventories/RUNTIME_PINS.json). They do not select the v5 model.

Use [SOURCE_LOCATIONS.json](sources/miata_handoff/Storage/inventories/SOURCE_LOCATIONS.json) to map exact saved receipts. Six selected audit/result records were local-only in the handoff and remain included here. The source package is not a full offline mirror: large corpora, runtime and complete raw logs remain on MIATA. A Git commit may omit ignored private artifacts; transfer manifests must enumerate actual files.

Do not copy credentials, SSH agent/control sockets, account caches or unrelated workloads. Historical `/Users/OODI/...` paths are provenance; resolve copied files through SOURCE_MANIFEST and validated path maps. Unix sockets and FIFOs are not portable experiment inputs. Do not alter runtime symlinks merely to make a copied path resolve.

## Unfinished successors

| **Preserved draft** | **Recorded completed work** | **Still required** |
| --- | --- | --- |
| DC retained recovery | Narrow adapter tests and original pending-prefix proofs | Real-prefix zero-call transition tests, byte-preserving import checks, worker integration, all-cell admission and new final auditor |
| ACE uniform-2048 | Nine tests and sixteen no-call source/config probes for seeds 42/43 | Scientific validation, controller integration and remote compatibility; not the v5 3-seed/full-panel profile |
| Joint follow-up scheduler | Six scheduling tests and earlier guard review | Final preparation/validation integration, child contracts and correct treatment of paused predecessors |

Drafts are preserved under [local_only](sources/miata_handoff/Storage/local_only). Their recorded tests have not been rerun as part of this document merge. Do not treat recorded readiness statements as proof of compatibility with v5.

The larger-cap DC runs reportedly continued repetition at the same failure boundaries. Regression checks should reproduce request formatting, stop handling and retry exhaustion on development/operational test inputs without placing diagnostics in the evaluation score pool. A failed update cannot become accepted memory because a status file was edited. A v5 failure-retention policy change would require explicit new scientific semantics and separate validation.
