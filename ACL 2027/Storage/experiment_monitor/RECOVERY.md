# Experiment monitoring and bounded recovery

The five-minute heartbeat now diagnoses stalls and repairs operational failures. It currently supervises the GoEmotions queue. The other datasets remain deliberately paused. A healthy run must not be interrupted to demonstrate recovery.

## Detection

Run `experiments/reporting/check_health.py` using the existing runtime313 Python. It persists metadata-only observations in this directory and does not modify experiments. Checkpoint counts, completed local model calls, process identity and Ollama reachability are inspected. An unchanged test prediction count during optimization is not sufficient evidence of a stall.

- A failed queue or missing matching process triggers immediate investigation at the next heartbeat.
- Preparation, prediction and judgment trigger investigation after no confirmed work for the greater of 300 seconds or ten recent median item durations. This allows the observed 143-second initial ICL prefill.
- Optimization uses the greater of 900 seconds or ten recent median durations. Inspect optimizer artifacts, completed calls and CPU activity before declaring it stalled.
- A threefold slowdown with continuing progress triggers resource diagnosis, not automatic termination.
- These thresholds initiate diagnosis. They are not proof of failure or permission for a blind restart. Five-minute scheduling means detection is not instantaneous; an ordinary stall may first be flagged roughly 5–10 minutes after progress stops. Host sleep, offline periods and missed scheduler wakeups can delay detection.

## Authorized repair

The heartbeat may correct operational code errors, handle transient local-server failures, repair recoverable append tails using the existing loader, and resume from validated checkpoints. For a confirmed hung owned runner, use a graceful interrupt and verify exit before starting exactly one replacement. Inspect actual command lines and the queue lock, not only a saved PID. Preserve all completed predictions, their order, reference labels, judgments and adaptation state. Restart only the currently prioritized GoEmotions queue. Do not resume intentionally paused datasets.

Before any mutation, save relevant queue/configuration/log metadata and affected implementation files under `incidents/<incident_id>/`. Never print source passages, model responses, demonstrations, reference annotations, playbooks or keys. Record the diagnosis and action in `actions.jsonl`. Only label recovery successful after fresh confirmed progress, not merely after creating a PID.

Never change model, quantization, seed, example count/order, context length, output caps, dataset splits, method, GT timing or evaluation rules to make an existing frozen run faster. Implementation bug fixes require targeted tests and explicit provenance describing why intended experimental semantics are preserved. Preserve the original frozen configuration and source hashes; do not blindly update hashes to bypass a mismatch. Changes that alter the protocol require a separately named run and user direction.

The local Ollama service may be restarted only if it is confirmed unhealthy and no unrelated workload would be interrupted. Do not kill unrelated applications or use broad process-name termination. Do not overwrite a valid judgment or retry a valid negative/null judgment to improve scores. Context overflow, output truncation and deterministic format errors need diagnosis rather than blind identical retries. DSPy optimizer restart can discard uncheckpointed search progress; inspect its resume capability before restarting it.

Preflight on 2026-09-13 confirmed that GEPA documents same-log-directory resume, while automatic restoration of MIPROv2 intermediate search state is not established. MIPROv2 finished compiled artifacts and local response caches can be reused, but neither proves that trial/search state resumes. Inspect internal progress before interrupting MIPROv2. See `incidents/method_preflight_20260913/REVIEW.md` for the repaired ACE reflection/reference-validation failures and corrected DC budget metadata.

## Retry and reporting limits

Allow at most two automatic restart attempts for the same failure signature in any rolling 30-minute window. Check `actions.jsonl` before acting. If the same failure recurs, stop restart attempts, preserve evidence, report the unresolved cause and continue read-only monitoring. The heartbeat stays active while recovery is pending; it is paused only after the full queue completes or the user explicitly pauses monitoring/work.

Each report includes current progress, recent throughput, provisional stage ETA, health classification and any incident. Distinguish no-progress duration, estimated delay and confirmed lost time. Report the actual repair, checkpoint retained, fresh progress after repair and any unresolved limitation. Do not call normal inference or optimization time wasted time without evidence.

After every observation or repair, run `experiments/reporting/update_results.py` to refresh the shared RESULTS.md and METRICS.md. No Notion or manuscript update is part of recovery.
