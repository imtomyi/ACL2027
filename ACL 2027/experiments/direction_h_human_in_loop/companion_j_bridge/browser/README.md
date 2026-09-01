# Exact Direction J browser lane for Charlie

Status: **prepared, not activated, no ratings or results**  
Scope: 24 fictional synthetic theme-and-evidence items

This is the runnable companion lane. It presents Direction J's exact item bytes
and complete shared guide, writes the exact unwrapped
`direction-j-shared-rating-v1` object, stops the rating timer before Direction H
feedback, and retains Direction J's active-time components: wall, hidden,
visible-idle-paused, and active time.

The browser display hides candidate identity, condition, and other ratings. On
Charlie's shared developer account this is conservatively classified as
**condition-masked developer review**, not secure technical blinding. Charlie's
data remain a developer-researcher case baseline and never become independent
human ground truth.

## Before an item can be displayed

A non-Charlie coordinator must complete all of these prospectively:

1. give Charlie the complete Direction J guide and the excluded fictional
   tutorial in `tutorial/`;
2. score the actual comprehension response using the coordinator-only key;
3. record actual qualifications, comprehension status, and synthetic-corpus
   familiarity in an exact Direction J actor registry;
4. run the prepared-only preflight and confirm there are zero responses;
5. create `activation_record.json` from the incomplete template, binding the
   exact manifest, queue, guide, schemas, actor registry, and comprehension
   record; and
6. choose this queue and retire the overlapping four-item full-output queue for
   this phase before any response is inspected.

The reviewer cannot self-activate the queue. The server blocks before item
display if any gate or hash is missing.

## Commands

From `experiments/direction_h_human_in_loop/`, the safe first preflight is:

```bash
python3 scripts/validate_direction_j_browser.py --prepared-only
```

After a non-Charlie coordinator has created the two completed qualification
records and `browser/activation_record.json`, verify activation without serving:

```bash
python3 scripts/validate_direction_j_browser.py
```

Only then start the loopback-only reviewer:

```bash
python3 scripts/serve_direction_j_browser.py
```

Open the displayed `127.0.0.1` address. The server exposes only the shared
guide, the next assigned fictional item, and Charlie's current response. Each
rating and timing receipt commit first and are immutable; an interrupted
feedback step resumes without reopening the rating. Feedback locations use JSON
Pointers from the evaluator-item root but may target only the proposed
interpretation or candidate assertion fields—not displayed text or actual
provenance.

After all 24 rating/timing/feedback sets exist, a non-Charlie coordinator locks
them before opening the private item key:

```bash
python3 scripts/lock_direction_j_browser_reviews.py --locked-by <coordinator-pseudonym>
```

The coordinator may then create exact Direction J observation envelopes through
the private post-lock join:

```bash
python3 scripts/finalize_direction_j_charlie_observations.py
```

Neither command computes a result. Do not edit response files, substitute an
item, open the private key before lock, or use protected real text.

## Timing rule

The active timer begins on the second animation frame after the complete guide
and item are in the DOM. Hidden intervals do not count. A visible idle interval
counts through 120 seconds after the last keyboard, pointer, or scroll event,
pauses thereafter, and resumes only on the next such visible event. Rating
submission stops the timer before feedback. The server validates chronology,
segment continuity, and duration reconciliation before locking a response.

## Downstream repair

The sibling `../theme_revision/` extension is the only compatible feedback-vs-
no-feedback repair path for these theme-level items. The old Direction H
full-output revision schema is a different task and must not receive this
feedback.
