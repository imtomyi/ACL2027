# Direction H reviewer preparation portal

This nontechnical, text-free page lets Charlie read three reviewer commitments
and see the current safe-metadata readiness state. It is separate from the
shared Warrant Study app and has no corpus loader, item bank, rating form,
response store, database, or model integration.

The page accepts only three fixed acknowledgments held in page memory. It has no
name, email, or free-text field and uses no cookie, browser storage, analytics,
or request log.

## Start locally

```bash
cd experiments/direction_h_human_in_loop/active_real_data/reviewer_portal
python3 server.py
```

Then open `http://127.0.0.1:8765`. The server refuses a non-localhost bind.

## Safety boundary

The server invokes the adjacent governance-only checker and validates its
reduced, text-free response. Both corpora must independently report exactly
10/10 complete gates, no blockers, and `real_text_ready=true`. Missing files,
checker errors, unknown gates, malformed output, inconsistent counts, or an
incomplete corpus keep the page locked.

Even after a future 10/10 result, this portal returns only an
onboarding-complete handoff. It contains no route capable of returning research
text or ratings. A separately approved restricted packet service would still
have to be connected later.

## Verify

```bash
python3 -m unittest discover -s tests -v
```

Tests use in-memory metadata states only and do not open either dataset.
