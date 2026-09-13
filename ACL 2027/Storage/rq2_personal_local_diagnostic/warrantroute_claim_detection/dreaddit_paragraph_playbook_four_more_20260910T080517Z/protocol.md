# Four Additional Flaw-Detection Guidelines

Controller: `dreaddit-playbook-four-more-v1`.
Model contract: `dreaddit-paragraph-playbook-followup-v1`, unchanged.

## Objective

Continue the completed paragraph follow-up to seek four additional distinct
Playbook rule IDs. These rules guide flaw detection and categorization, not
experiment administration, general coding, or manuscript policy. They are
fallible checking procedures, not gold answers.

The user also authorized additional data points. Select four NEW original
Dreaddit development paragraphs from the same frozen source inventory, keeping
their full texts. The pinned local Gemma 3 4B, decoding options, role prompts,
generated-output schema, immutable
seed protections, evidence checks, and all six audit criteria are retained.
The previous final memory is carried forward exactly, including its stable TXT
IDs and support metadata. Its documented semantic limitations are not erased or
requalified by this continuation. Do not reset the Playbook to seeds.

## Scope and Stop Rules

- Exclude the evaluation panel and previously used records, source groups, and
  normalized text. Use only the existing `development_train` inventory. Select
  the first four eligible paragraphs in canonical source packet/excerpt order
  before any new outcome. Do not select sources based on anticipated flaws.
- Each new data point is one full original paragraph, not its parent constructed
  claim. Do not pass source labels, stress metadata, or generated claim labels
  to the model. Log source record IDs and parent packet provenance.
- Schedule three epochs of these four new paragraphs, for at most 12 further
  exposures. Epochs 1-3 refer to this NEW panel; the carried memory is never reset
  between panels or epochs. Early target/budget stops may leave epochs incomplete.
- A rule counts only when a receipt records `added` with a canonical ID absent
  from both the initial memory and earlier additions in this run.
- Refinement, reinforcement, an inherited rule, and replay of a previous result
  do not count toward the four new rules. Exact duplicate checks remain active.
- Stop once at least four new IDs have been admitted and the first four each
  appear in a subsequent valid detector's actual request. Check the exact TXT
  and rule-index bindings. Delivery does not imply correct use.
- A single query may admit two valid additions. Retain both if the target is
  exceeded; never discard a valid output selectively to manufacture an exact
  final count. Do not manufacture or force an addition when no lesson qualifies.
- Stop at 12 completed additional queries, 36 local calls, or a 600-second
  inference budget, whichever occurs first. Preserve partial stages when the
  inherited 181-second call-admission reserve closes execution.
- An unmet target is reported honestly. Do not extend limits or rerun rejected
  outputs automatically. Honor a query-boundary pause request.

## Persistence and Controls

Store the continuation separately. Freeze inputs, initial state, prompts, code,
schedule, and stopping policy before inference. Preserve all old outputs and
manifests. Publish a stable-ID TXT after every completed query and retain revision
history, unchanged decisions, failed proposals, and audit receipts.

Use the existing shared worker lock and local Ollama ownership controls. No
duplicate workers, paid APIs, model downloads, or changes to previous runs are
permitted. Contract/hash errors and ambiguous requests require attention, not
silent retries. No change to `AGENTS.md` is required for this private diagnostic.

## Reporting and Interpretation

Keep initial/after TXT snapshots, an exact diff, per-query outcomes, current and
new rule counts, distinct newly delivered IDs, request journals, and a final
manifest. Report actual additional and cumulative exposures, not an inflated
number of independent samples.

The stop depends on observing a requested number of admitted rules. This is
development debugging, not an unbiased performance estimate. The model auditor
can approve weak rules and the detector can misapply delivered rules. Inspect
actual rule text and usage before claiming success beyond storage and delivery.

No adjudicated flaw inventory is available for these paragraph-native inputs.
Accuracy, precision, recall, Credibility, and Conformability remain unassessed.
Do not update Table 3, manuscript results, or claim that memory growth proves
better flaw detection. Separate offline fixtures from live inference artifacts.
