# Browser responses

Prepared state: no responses, ratings, timing receipts, feedback, locks, or
results exist.

When prospectively activated, the server creates one atomic immutable directory
per frozen assignment under `locked/`. It contains only `rating.json` (the exact
unwrapped Direction J shared rating) and `timing_receipt.json`. A later atomic
`feedback_commit/feedback.json` sidecar completes that item. A locked rating is
never edited; if feedback is absent after an interruption, the next browser
session resumes feedback for that same item.

After all 24 sidecars are complete, a non-Charlie coordinator closes the write
window by creating `first_stage_lock.json`. No such file exists in the prepared
package.
