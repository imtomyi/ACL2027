# New Dreaddit Paragraph Panel

Controller: `dreaddit-new-paragraph-panel-v1`.
Model contract: `dreaddit-paragraph-playbook-followup-v1`, unchanged.

## Current Request

Run exactly 12 additional, distinct Dreaddit data points. Do not run GoEmotions,
CaChe, or ParlaMint-GB. A data point is one complete original paragraph. Existing
Playbook state is carried forward, not reset. These are flaw-detection and
categorization guidelines, not thematic codes, revised documents, or answer keys.

The preceding runs used records 127-130 and 159-162. Exclude every record, source
group, and normalized text from the entire frozen run ancestry, not only the
immediate parent. Also exclude the existing frozen evaluation panel. Select only
`development_train` records, in canonical source packet/excerpt order before new
outcomes. Preserve original paragraph text and provenance. Do not supply the
parent packet's constructed claim, stress label, or other answer-like metadata.

## Fixed Execution Contract

- Same pinned local Gemma 3 4B, decoding options, paragraph-native role prompts,
  generated-output schema, seed protections, and six audit criteria.
- Initial memory is the last terminal state's full JSON, including stable rule
  IDs and support metadata. Its known semantic limitations remain unqualified.
- Twelve new paragraphs over at most three epochs: 36 possible exposures, not
  36 independent data points. Retain memory across all paragraphs and epochs.
- First complete at least one query for EACH of the 12 new paragraphs. Only then
  may the inherited four-new-rule target stop execution early, provided all four
  first admitted new IDs have appeared in a later valid detector request.
- If that target is not met, continue through the remaining prespecified epochs,
  subject to the time/call limits. Do not force additions or silently convert
  reflections into rules. Empty patches and rejected proposals remain outcomes.
- At most 108 local model calls and 1,200 seconds of inference. The inherited
  180-second per-call timeout and 181-second admission reserve remain active.
  Budget closure may leave an unfinished stage; preserve and report it.
- Only newly admitted rule IDs count. Refinement, reinforcement, inheritance,
  repeated delivery, and TXT writes do not count as new guidelines.
- No paid API calls, downloads, duplicate workers, or automatic reruns of failed
  or unfavorable responses. Respect the shared lock and query-boundary pauses.

## Files and Reporting

Freeze the full selection, ancestry, initial state, prompts, implementation,
schedule, and parameters before inference. Report coverage out of 12 separately
from exposures out of 36. Record the actual numbers, including an unmet target.

Keep readable `data_points.md`, canonical `inputs.private.json`, per-query CSV,
initial and after Playbook TXT, exact diff, revision history, immutable call
journals and result chains, status, and a final manifest. Never alter old runs.

This is outcome-stopped development debugging with no adjudicated flaw inventory.
Neither a rule admission nor its delivery proves correctness, useful application,
or improved detection. Accuracy, precision, recall, Credibility, and Conformability
remain unassessed. Do not update Table 3, manuscript text, or manuscript results.

The driver accepts a frozen panel size, epoch count, time budget, and target at
preparation time so future authorized panels need not change the implementation.
Changing those values after preparation is prohibited.
