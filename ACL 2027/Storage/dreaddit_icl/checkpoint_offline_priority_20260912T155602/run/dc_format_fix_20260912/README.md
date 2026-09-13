# DC format-handling amendment — 2026-09-12

The local adapter stopped DC GT ✓ after four saved predictions because the curator did not return a complete `<cheatsheet>...</cheatsheet>` wrapper. The original failed response was not retained; the failure itself was recorded. On resume, the fifth item returned an incomplete memory document despite a normal model stop. Its two format-only repair attempts did not yield a valid complete wrapper, so the previous memory was retained and this outcome was explicitly checkpointed.

The amended adapter accepts a single complete nonempty wrapper, attempts at most two structured format-only repairs, and otherwise retains the previous memory. This fallback follows upstream's missing-wrapper behavior. Repair calls are an additional local adaptation and must be disclosed when reporting reproduction fidelity. The same adapter is used for both DC GT conditions. No test label reaches the prediction call; GT feedback remains curator-only after prediction.

Prediction and curator checkpoints are stored in each method's `dc_steps/` directory. These contain local model output and should not be published unreviewed. A completed checkpoint can be replayed without another prediction. Already saved predictions were not changed. The original failed fifth prediction was unavailable, so that unsaved item was generated again.

Validation: eight adapter contract tests passed, including GT feedback isolation, malformed-wrapper rejection, bounded repair, fallback and completed-checkpoint replay. Live resumption passed the previously failing fifth item. This is a recovery of queue execution; retaining memory is not counted as a successful memory update.

The prediction supervisor was restarted, followed by the Conformability worker in waiting mode to avoid concurrent model inference. Existing quality judgments are preserved. The five-minute progress heartbeat remains active.

Files prefixed `before_` and `after_`, state backups, and `amendment.json` preserve the change record. The original experiment snapshot was not overwritten.
