# Active Dreaddit run

The six local conditions are queued: Base, ICL, MIPROv2 heavy, GEPA heavy, DC-CU GT yes, DC-CU strict GT no. GPT-5 awaits API setup; no cloud dataset requests were made. ACE is excluded.

RESULTS.md is updated after every committed test item and shows accuracy only after all 712 items finish. All raw outputs and checkpoints remain local. This is a method-transfer diagnostic, not an exact ACE finance reproduction or a publication-ready frozen result.

Official DSPy 3.0.3 implements MIPROv2 and GEPA. The pinned DC source executes the cumulative workflow without code execution. DC retains its generator cap 2048 and curator cap 4096; other calls cap at 4096. All use native Qwen3-8B Q4_K_M with thinking off and 32768 context. Base/ICL use the same brief reasoning and answer-tag task instruction. DSPy uses its official typed-output adapter. DC uses its official generator/curator templates plus the shared classification task. These wrapper differences are recorded rather than claimed identical.

Four software contract tests passed: parsing and invalid-output denominator, post-disjoint splits and source hash, official DC feedback noninterference, and DSPy transport/cache. No mock response is included in experimental scores.

The supervisor runs one method at a time, stops the queue on any method failure, and preserves committed checkpoints. Rerunning the supervisor resumes evaluation checkpoints. Interrupted DSPy optimization restarts compilation with a persistent response cache; this is not a guarantee of exact mid-search resume. Failed memory updates do not commit the corresponding sample. Caffeinate prevents idle sleep while the supervisor is alive; lid closure and shutdown can still interrupt it.

The five-minute Codex monitor is read-only and reports failures. It does not silently restart or change the experiment. The earlier timing figures were planning assumptions; use measured calls and completed items for updated ETA.
