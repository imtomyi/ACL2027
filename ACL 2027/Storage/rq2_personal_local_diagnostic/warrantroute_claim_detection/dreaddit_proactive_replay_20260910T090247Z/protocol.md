# Proactive Dreaddit Replay v1

## Objective and Scope

Test whether explicit candidate discovery and feedback across epochs produce
more admitted, reusable flaw-detection checking procedures. The goal is flaw
detection and correct categorization, not theme generation or document repair.
Rule growth is an operational outcome, not evidence of improved accuracy.

Replay the exact 12 original Dreaddit paragraphs and all 36 scheduled exposures
from the completed `dreaddit_playbook_new12_20260910T083622Z` comparator. Start
with its INITIAL three-rule memory, not a manually improved or terminal memory.
Inputs, initial state and schedule must match byte-for-byte. Every paragraph is
one complete original paragraph, repeated once in each of three epochs. These
are 12 distinct data points, not 36 independent samples or fresh held-out data.
Preserve the comparator and all historical outputs. No other dataset is run.

## Fixed and Changed Components

- Same pinned local Gemma 3 4B model, temperature 0, seed, context and token limits.
- Same detector and auditor prompts, schemas, exact-evidence checks, immutable
  seeds, six-criterion semantic audit, memory capacity and four-learned-slot retrieval.
- Same locked-prediction-before-learning sequence and stable admitted `shr-` IDs.
- Changed learning prompt and schema: require exactly four short, grounded
  opportunity assessments, in the order flaw detection, false-positive
  prevention, category disambiguation and evidence sufficiency.
- Changed learning input: include only the latest earlier committed learning
  decision for the same paragraph in THIS run, including proposed fields,
  receipts and failed audit criteria. No comparator predictions or decisions,
  gold labels, external judgments, held-out examples or future queries enter it.
- At most two candidate patches per query, in one combined Reflector/Curator call.
  There is no forced minimum. Add only a new substantive condition or procedure.
  Refine a learned rule when correcting its existing boundary. Do not inflate
  counts through paraphrases, unnecessary splitting, reinforcement or retries.

## Candidate and Admission Rules

Every candidate must specify an observable input trigger, an actionable check,
the textual evidence required to substantiate a flaw, and a general exception
that preserves genuine detection. Output labels are not applicability conditions.
Personal reports and questions are not automatically flaws. Source-specific
conclusions, identifiers and copied passages cannot become reusable rules.

Search actively for a defensible new procedure or an over-detection safeguard.
When previous proposals were rejected, use the actual recorded reason to improve
the underlying procedure. An unchanged rejected proposal is not progress.
When no grounded novel lesson exists, retain an explicit no-change decision.
No manually authored candidate is inserted as though it were model-learned.

Candidates receive deterministic `cand-` content identities, retained across
repeated occurrences. Their TXT register and immutable per-query history remain
separate from the active Playbook. Content-distinct IDs do not prove conceptual
novelty. Refine and reinforce candidates are not counted as newly admitted rules.
Only accepted add operations introduce a new active `shr-xxxxx` ID. All existing
evidence, novelty, countercondition and capacity checks remain mandatory. The
same model's audit is fallible, not independent semantic validation.

## Execution and Failure Handling

Complete all 36 exposures regardless of how many rules are admitted. There is no
four-rule or favorable-outcome early stop. The local-only resource ceiling is
108 calls and 90 minutes, with at most one detector, one learning and one audit
call per query. The larger time ceiling permits the requested full replay when
more candidates require audits; it is not an ETA. No paid API calls or downloads.

Use the shared inference lock and a run-local worker lock. Freeze code, prompts,
inputs and configuration before starting. Preserve request and response hashes,
prediction locks, state chains, receipts, candidate history and TXT revisions.
Do not retry a failed or unfavorable generation to change its outcome. Report
technical failures separately. Stop for ambiguous calls or frozen-contract
errors; a requested pause takes effect at the next query boundary. Clean up only
an Ollama server started by this worker. A terminal replay cannot be resumed.

## Reporting and Verification

Report completed exposures out of 36 and distinct paragraph coverage out of 12.
Separate candidate occurrences, distinct candidate contents, admitted new IDs,
refinements, reinforcements, rejected candidates and actual subsequent detector
delivery. Keep initial and after TXT files with an exact diff. Compare the
observed operational counts with the original run without merging the runs.

Verify paired inputs, schedule and initial memory, complete result chains,
request/response bindings, actual retrieved TXT in detector prompts, and all
frozen/final manifest hashes. Spot-check admitted rule text for circularity,
source memorization and over-detection risks; do not silently edit it afterward.
Accuracy, precision, recall, Credibility and Conformability remain unassessed:
there is no adjudicated flaw inventory for these paragraph inputs. Do not export
these debugging results into Table 3 or a manuscript as validated performance.

## Offline Test Plan

Test the learning schema, explicit no-change path, stable candidate IDs,
unchanged detector/auditor requests, previous-only same-paragraph feedback,
immutable comparison inputs, seed protection and unchanged rejection behavior.
Exercise all 36 jobs even after four additions, paused and terminal states, TXT
delivery, candidate history and final manifest validation. All fabricated test
fixtures remain temporary files under Storage and are not experimental results.
