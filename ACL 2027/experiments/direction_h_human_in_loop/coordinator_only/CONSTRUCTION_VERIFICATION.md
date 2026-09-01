# Independent construction check before detection scoring

The four tasks may be used immediately to qualify collection mechanics. They
must not be used to estimate target detection or control false positives until a
non-Charlie verifier who did not construct the items completes this check.

The verifier reviews the original blinded source output named in `truth_map.json`,
the reviewer-safe derived item, and the intended transformation. For each task,
the verifier determines whether the intended manipulation is actually present,
the canonical target flag is appropriate, a second material manipulation is
absent, and the no-planted-defect control is materially adequate under the
bounded contract. “No planted defect” by itself is not a clean-truth label.

Copy `construction_verification.template.json` to
`construction_verification.json` only when an eligible verifier begins. Replace
every `__REQUIRED...__` value from actual review; do not prefill a favorable
disposition. Validate the completed record with the coordinator preflight.

Eligibility is itemwise. A task enters revision and target-repair assessment
only when its committed truth is `controlled_defect` and its item disposition
is `verified_for_detection`. A `workflow_only` or `reject_item` task stays in
the private exclusion inventory; it does not veto a different eligible target.
Likewise, the overall disposition and the disposition of a no-planted-defect
control are retained for audit but do not veto an eligible target. At least one
eligible controlled target is required to build revision cases. No verifier may
change the committed condition or target flag.

This record contains condition truth and stays coordinator-only. Charlie must
not open it while rating.
