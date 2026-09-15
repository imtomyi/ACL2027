# Server v5 execution status

Qwen3-8B is the selected first backbone. The shared SSH connection works. Historical server results and the old paused local run remain separate.

- Base/ICL stage: finished all 1,800 attempts across 18 seed runs; 1,738 valid predictions and 62 committed format failures. Ten runs have 100 valid predictions; eight have format failures. These are prediction results, not fully judged rows.
- The joint ACE/DC queue ended at 2026-09-14 09:22:05 UTC with all 36 r3 ACE trajectories complete and 16/18 r4 DC trajectories complete. It treated two failed DC runs as terminal and did not retry them or launch the unfinished optimizer/judge stages. The eight GPUs subsequently became idle.
- Recovery `dc-r4-unicode-transport-recovery-v1` launched at 09:49:04 UTC under `recovery_dc_20260914_1`: CaChe GT ✗ seed44 resumes from 17 predictions/16 updates on GPU7; GoEmotions GT ✓ seed44 resumes from 20 predictions/19 updates on GPU1. CaChe had an unpaired Unicode surrogate in its saved curator JSON; GoEmotions had an incomplete inference response. The wrapper rejects invalid Unicode at the existing format-validation boundary and uses existing bounded request retries. It changes no prompts, requested schemas, model, seeds, order or budgets and preserves raw failed calls, committed predictions, memories and original GT-access receipts. Five software tests and 36 cached development curator outputs passed. Source files named by the r4 seal remain unchanged. See [recovery validation](recovery_dc_20260914_1/VALIDATION.json) and [live recovery queue](recovery_dc_20260914_1/queue.json).
- Recovery outcome as of 09:54 UTC: CaChe passed the failed update and is advancing beyond 30/100. GoEmotions exhausted its remaining two transport attempts and remains failed at 20 predictions/19 updates. A separately recorded 19.3-second backend diagnostic returned HTTP 200, `done=false`, and partial JSON ending in repeated zeros. Ollama v0.33.3 `llm/llama_server.go` aborts after more than 30 repeated token chunks without a final Done callback, explaining this reproducible response. It is a model-output repetition failure, not SSH authentication or memory exhaustion. The diagnostic is not used as a prediction or memory. All 135 original CaChe evidence files and 178 original GoEmotions files were byte-identical at the first recovery audit. Do not reset the exhausted request budget or silently alter the completed rows. Any further scientific output-format change needs a declared revision and development validation.
- All 330 saved ACE prediction/update files were checked after resumption and are byte-identical. ACE was resumed from checkpoints, not rerun. r1, r2 and superseded r3 DC artifacts remain preserved. Interrupted calls are never counted as successful.
- Fifteen r4 software checks and the real development checkpoint/GT-order audit passed. Current admitted rows have no withheld development failures. New production errors, if any, remain visible and are investigated by the monitor; passing a development gate does not guarantee every future model call succeeds.
- MIPROv2/GEPA: 12 seed runs remain unstarted; mapping their optimization objectives to the pinned APIs is unfinished.
- Judging: not started; primary judge selection/calibration is unresolved. Conformability remains pending. Expanded metrics are only final where their prerequisites and exporters exist.

The full planned panel is 84 seed runs and 8,400 evaluation predictions over 400 unique evaluation records. Every corpus has 100 train, 100 development and 100 evaluation records. Seeds are 42, 43 and 44. This is a previously observed evaluation panel, not an untouched confirmatory holdout.

CaChe and ParlaMint-GB have no validated label GT, so accuracy stays N/A. GoEmotions retains official neutral co-labels. Literal quote matching and raw reported offset validity remain distinct from LLM-judged Conformability.

Server root: `/home/sy23985/Storage/acl2027_server_v5_20260914`.

- [Base/ICL results](live/RESULTS.md) and [metrics](live/METRICS.md)
- [Repair and handoff review](adaptation_r4/HANDOFF_REVIEW.md) · [Current pipeline metadata](joint_adaptation/queue.json) · [Historical r1 results](adaptation_r1/RESULTS.md)
- [Original immutable design](../experiment_guidelines/four_corpus_server_v5/GUIDELINES.md)

Server reports refresh roughly every 15–20 seconds while a controller is active. Local reports are mirrors refreshed by the hourly monitor and manual status checks. Files named in either execution manifest must remain immutable. An empty queue with optimizer/judge work unstarted is an incomplete pipeline, not successful completion.

Terminal: run `~/acl-progress` in the server SSH session for a live five-second view. [Viewer options](TERMINAL_PROGRESS.md).

Consolidated results: [v5_results.md](../v5_results.md), including 28 condition summaries and all 84 seed rows.

Future sample sizes: [configuration guide](DATASET_SIZE_CONFIGURATION.md). This prepared successor does not alter the current 100-item panels.
