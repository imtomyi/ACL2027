# First V2 Preflight Failure

This is a software preflight record, not an experimental result. No held-out
evaluation packets were used. Original calls and output files remain unchanged.

The test stopped on the first GoEmotions development packet while checking a
rejected Playbook proposal. The audit response had no qualifying evidence and
`audit_approved` raised `invalid_audit_evidence` instead of withholding the patch.
No experimental supervisor was launched from this preflight.

The subsequent code revision preserves the same approval requirement: exact
support and all six true flags are required. A complete rejection, unknown
assessment, or insufficiently supported approval now withholds the update rather
than throwing a transport-style exception. A new preflight directory tests the
entire eight-packet development panel again. Failed and successful smoke outcomes
are never selected or imported as experimental quality measurements.
