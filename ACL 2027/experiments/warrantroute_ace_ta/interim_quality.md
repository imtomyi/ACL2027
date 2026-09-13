# Interim quality addendum

Authorized on 2026-09-09. This additive monitor does not modify the frozen parent
runner, prompts, inputs, model digests, memory, scoring or generation order.
The primary experiment already judges each batch of 50 outputs, with 50/100
checkpoints. All four methods remain in that experiment.

## Early development diagnostics

Run interim_quality.py tick at most once per five-minute monitor check. It
reuses the 12 existing qualification judgments after verifying the exact prompt,
schema, model and source artifact. For further completed development episodes it
makes at most one additional local Qwen judgment per tick. Selection is ascending
episode number then path, never score-based. Each successful output is judged
once. Failed generation is technical missingness, not a semantic failure or pass.
No retries for failed, unknown or unfavorable judgments. Retained in-flight
journals cannot be resubmitted. A separate lock prevents duplicate sidecar calls.

Judging uses the frozen TA rubric, source evidence and final artifact only.
Model identity, method label, episode, memory and prior score are hidden from the
judge. The qualification-stage seed is reused for additional development judging.
The main evaluation-stage seed remains unchanged. Do not pool phases.

Development diagnostics are exploratory and previously exposed, not held-out
performance. Accepted updater operations are not evidence of quality. Judge
findings never enter model feedback, Playbooks, routing or selection. Shared-Qwen
judge bias and small sample limitations must be disclosed. Additional inference
competes for local Ollama time; account for its calls/tokens separately and do
not present its timing as primary-run inference speed.

## Comparisons

Report Credibility, Conformability and evidence coverage using T, F, U,
technical missingness, pending and the binary denominator. Percentages are
T/(T+F). Pending outputs are not implicitly passes or failures. Main evaluation
keeps 100 planned packets per cell; use the primary export for planned coverage.

Read primary evaluation judgments as they appear. Compare methods within a
dataset/model and models within a dataset/method using identical packet IDs and
source-task hashes. Report paired percentage-point differences, joint binary n,
left-only passes, right-only passes, ties and exclusions. A zero denominator
means unavailable. Comparisons on a few cases are descriptive, not evidence of
superiority. Never compare unmatched prefixes, mix development and evaluation,
or infer significance from repeated interim inspection. Preserve CaChe's
within-source diagnostic qualifier.

The historical n100 experiment judged claim-review quality. The current run
judges generated TA codes/themes. Its historical export is snapshotted for
reference, but the different task and rubric block numerical improvement claims.
Even identical underlying source packets do not resolve this incompatibility.
A valid old-versus-new architecture comparison would require a separately
specified, matched TA experiment; this sidecar does not silently launch one.

## Monitoring behavior

Every five minutes report progress plus the latest quality counts, their sample
sizes and change from the prior check. Where comparable paired results exist,
say which side is higher or lower, with the exact n and exclusions. Where absent,
say comparison pending. Summarize decisive judge concerns without exposing
private participant text. Report errors; never fix or restart the experiment.
Report-only command refreshes summaries with no inference. All sidecar files
are under the parent run's interim_quality directory and excluded from official
Table 3, frozen Playbooks, checkpoint selection and manuscript evidence.
