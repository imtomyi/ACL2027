# Two-hour-per-dataset diagnostic pilot

User-authorized protocol replacement on 2026-09-13. Original run directories, predictions, optimization artifacts, and frozen settings are preserved. The earlier live GoEmotions MIPROv2 was interrupted at user request; its in-memory search is not claimed to be resumable. This run starts fresh.

- Serial order: GoEmotions, Dreaddit, CaChe, ParlaMint-GB. Maximum 7,200 seconds per dataset, with at most 55 seconds of termination grace. No automatic deadline extension.
- GoEmotions: 32 train, 32 dev, 128 test; Base, ICL, MIPROv2, GEPA.
- Dreaddit: 32 train, 24 validation, 24 test; same four plus DC GT yes/no.
- CaChe and ParlaMint-GB: each 4 adaptation and 8 test excerpts, Base and six ACE/DC GT yes/no variants. Seven rows each. Supervision is unverified Qwen pseudo-labels, not human GT.
- Fixed record-ID hash sampling with seed string 42, shared test subset and order across methods; no outcome-driven selection. Original train/dev/test separation is retained. Topic pilots retain source-session separation.
- ICL: 8 training examples. MIPROv2: official DSPy implementation, auto=None, 2 candidates, 4 full-dev trials, up to 2 bootstrapped and 4 labeled demos. GEPA: official implementation, auto=None, max_metric_calls=96. This is deliberately reduced-budget method transfer, not full paper reproduction.
- Model and role token caps retained. Dreaddit direct classification now uses structured single-label JSON; DC retains its existing answer-tag adapter. These protocol changes are explicit and are not mixed with old runs.
- Every method receives the same selected test subset. Full-test predictions/scores are not reused. Pseudo-references are sealed before topic comparisons. Predictions precede online label feedback. Conformability never feeds adaptation.
- Acc and exact-set agreement remain separate. Micro/macro F1 accompany supervised Acc. All conformability judgments must resolve before final pass-rate display. Partial runs stay incomplete at the deadline.
- Small sample sizes prioritize a diagnostic run under the time ceiling, not precise comparative conclusions. Deadline completion does not imply completion of all method rows.
- GPT-5, supervised ACE, and ICL/MIPROv2/GEPA for the provisional topic tasks remain outside the existing implemented scope.
