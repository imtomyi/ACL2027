# Handoff review for adaptation r2

Reviewed the MIATA handoff in `/Users/tom/Downloads/Server/`: README, RESULT_MATRIX, FILE_MAP, SCIENTIFIC_HANDOVER, NEXT_OPERATOR_RUNBOOK, DECISIONS, source inventories, retained-memory DC recovery, ACE worker contract and joint-scheduler stop handoffs. The archived stop instructions describe the historical run. The current user has authorized fresh v5 execution and repairs.

The local integrity verifier passed all 868 manifest files. This is a checksum verification, not a claim to have manually read every private raw response. Nine reused ACE/DC source and prompt files were also compared with their actual historical MIATA copies: all nine whole-file SHA256 values match (HANDOFF_SOURCE_CHECK.json). Python-version-dependent AST dumps are not used as integrity checks.

## Findings applied

- Reuse the preserved Python 3.13.2, Ollama 0.33.3, Qwen3-8B model digest and pinned tokenizer. Check current process ownership and serialize use of the eight experiment services. Leave the shared port 11434 and other users' processes alone.
- Preserve serial updates within each stream, stable ACE IDs and counters, durable prediction-before-GT commits, separate call receipts and checkpoint replay. A prediction is not a completed update.
- The old DC 8192 experiment still failed with repetitive truncated outputs. Raising caps alone was insufficient. The current r1 development failures additionally prove missing wrappers, evidence assigned outside the selected labels and conflicting abstention labels. r2 changes serialization to prevent those structural contradictions. It does not change selected labels using GT.
- All 18 development conditions must pass six real development sources and six updates before any of the 54 fresh ACE/DC seed runs are admitted. Train/test panels, orders, seeds, model, context and role caps, 4096-token memory budget and canonical scoring remain unchanged. r1 is preserved under its original source seal.

## Historical material kept separate

The original 27/30 audited matrix, all 12 historical ACE rows, and the separately audited DC8192 results have different sample counts, caps, reference banks or seeds. They are not imported as v5 results. The local retained-memory recovery and joint scheduler were unfinished, unlaunched drafts. Their policy of retaining memory after a proved length failure is not silently adopted: exhausted malformed or truncated adaptive calls still stop their condition. The current v5 policy only retains prior memory for a complete, valid proposal exceeding the memory budget.

Historical CaChe/ParlaMint model-reference agreement is not human accuracy. Current GTX rows retain Accuracy=N/A. Conformability remains pending judge selection. The handoff's prior paused monitor and old service ownership do not govern this new run; current ownership records and the five-minute monitor do.

This file documents operational and protocol provenance only. It contains no corpus text, model answers or manuscript claims.

## Revision r3 development follow-up

r2 reproduced the historical DC loop on real development inputs: the CaChe 8192-token response had 657 lines but only 42 unique lines. r2 never admitted production. Its terminated in-flight calls are preserved as interrupted, not successful. r3 uses 1-24 structured description/example/usage-count items with 160/320-character text bounds, rendered without trimming or deduplication. These additional method-specific format constraints are declared in REVISION.json; they change the free-form curator output space while keeping the runtime token and final memory budgets unchanged. All 18 development cases must pass afresh.

## DC-only revision r4

R3 passed development, but its production DC answer generators later repeated the explanation field. R4 adds a declared 1600-Unicode-character explanation limit for DC only. It passed six real development cases (36 predictions and 36 updates). The joint dispatcher resumes all 36 r3 ACE trajectories unchanged and uses 18 fresh r4 DC trajectories. All 330 saved ACE prediction/update files remained byte-identical after resumption. The original DC failures and interrupted requests remain separate evidence.
