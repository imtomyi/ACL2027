# Experiment Data Catalog

Start with [the offline packet viewer](index.html). It opens directly in a browser without a server, internet connection, model service or API key.

This is a restricted local inventory of the data actually associated with stored reviewer outputs in the Table 3 experiment family. It is not a new experiment, a release dataset or a manuscript export. Original inputs, outputs, queues and results are unchanged.

## Three Views

- **Dataset guide:** explains original corpora versus locally constructed packets,
  shows the 100-packet sample as five groups of 20, and pairs actual source
  excerpt previews with the corresponding constructed claim. Dataset and flaw
  selections update the example; Open this packet leads to its complete text.
- **Packet explorer:** retains all current and earlier packet entries, search,
  filters and exact source wording. Packet identifiers, source locations and
  construction metadata remain available in expandable sections. Linked reviewer
  outputs are explicitly labeled as historical baselines, not the active loop.
- **Scoring explained:** separates intended-flaw detection from review Credibility
  and Conformability, explains the same-model WarrantRoute conditions and the
  separate judge, and documents unresolved scores and interpretation limits.

The page opens on the dataset guide. These explanatory views do not claim to
show live experiment progress or new completed WarrantRoute results.

## What to Open

| File | Contents |
|---|---|
| [index.html](index.html) | Dataset explanation, interactive sample map, exact packet explorer, scoring definitions, provenance and historical prompt/review links. The packet explorer defaults to Table 3 n100. |
| [DATASET_BACKGROUND.md](DATASET_BACKGROUND.md) | English explanation of corpus origins, experiment construction, theoretical relevance and limitations. |
| [VERIFIED_INVENTORY.md](VERIFIED_INVENTORY.md) | Verified counts for current and earlier experiments, separated from prepared-only banks. |
| [packets_table3_n100.csv](packets_table3_n100.csv) | One row per current packet, including claim, intended flaw and file location. |
| [excerpts_table3_n100.csv](excerpts_table3_n100.csv) | All 1,600 displayed excerpts in the current 400 packets, including full text and source location. |
| [packets_all_observed.csv](packets_all_observed.csv) | Packet index including earlier runs. |
| [excerpts_all_observed.csv](excerpts_all_observed.csv) | Full excerpt index including earlier runs. |
| [reviewer_output_inventory.csv](reviewer_output_inventory.csv) | Existing reviewer file paths, statuses, model/role and hashes. Stored copies do not imply additional inference calls. |
| [quality_input_inventory.csv](quality_input_inventory.csv) | The 3,600 quality-input unit IDs, methods/models, source reviews and original JSONL line numbers. |
| [earlier_quality_output_inventory.csv](earlier_quality_output_inventory.csv) | Thirty earlier claim-quality records, kept separate from the current review-quality experiment. |
| [audit.json](audit.json) | Count, hash and source-text checks. |
| [catalog.json](catalog.json) | Complete machine-readable viewer data with exact packet text. |

## Reading a Packet

1. Choose Table 3 n100, a dataset and optionally an intended flaw or text search.
2. Select a packet. The claim is the text reviewed by the model. Source excerpts are the evidence available for that claim.
3. Read all displayed excerpts, including the ones not cited by the claim. A candidate_role field is not the authoritative citation list: the catalog checks cited_excerpt_ids.
4. Open provenance to find the source row, transcript line or parliamentary XML utterance. Read the full stored packet when the precise historical fields matter.
5. Open a historical prompt to inspect exactly what the role-based reviewer received. The quality-judge example is a separate input with a different role in the experiment.

The viewer and this document are in English, as requested for experiment documentation. Source text is preserved in its stored language and wording, including typos and sensitive content. No paraphrases are substituted for experimental input.

## Scope and Counting

The current set is bound to `table3_n100_prompt_identity_repair_v1.json`: four datasets, 100 packets per dataset and four excerpts per packet. Earlier observed use is detected from reviewer records, not queue manifests or bank names. Banks with no outputs are listed as prepared-only and their source texts are not added to the viewer.

An observed entry is a `(bank, corpus, packet_id)` combination. The same packet or source text can recur across earlier banks, methods, models or repaired copies. Do not count those as independent source documents or repeated independent participants. [The inventory](VERIFIED_INVENTORY.md) reports the distinct-ID counts separately.

The discovery scope is all direct packet banks under `Storage/draft_review_packets`, with an additional check for unmapped `PKT_*.json` files throughout `Storage`. This is a complete inventory for those stored reviewer records, not a claim to enumerate every unrelated experiment in the repository. WarrantRoute replays on these packets do not constitute a new source-text dataset.

## Integrity and Privacy

The builder checks frozen packet/truth hashes, all 3,600 repaired reviewer prompt hashes, and the claim/text and source-review hashes of all 3,600 current quality-input units. Every displayed excerpt is compared with the prepared source record or original normalized TSV/XML text. Raw location metadata remains linked for audit. This does not validate the scientific correctness of intended flaws or establish human-review/privacy clearance.

Local paths are linked to the current workspace. The HTML embeds its data, so packet reading works offline. Existing-source links require the workspace to remain at its current location. CSVs use UTF-8 with BOM for Excel. Formula-like cells are prefixed with an apostrophe for spreadsheet safety; JSON and packet snapshots preserve exact text.

One excerpt in the initial draft experiment differs from its prepared analysis record only in repeated spaces. Its original packet wording is preserved and the difference is marked in the viewer and audit. All current n100 excerpt texts match their prepared sources exactly under the recorded TSV/XML normalization.

All artifacts stay under `Storage/`, with restricted local file permissions. Do not publish this directory, commit source text, attach it to a manuscript, or send it to an external model without the required permissions and project review.

## Rebuild

Run the local builder after an authorized input change:

```sh
python3 "/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_data_catalog/build_catalog.py"
```

It reads existing artifacts and rewrites only this catalog directory. It makes no inference calls and modifies no source records or experiment results. An integrity mismatch stops the build instead of silently substituting data. Browser checks are recorded in `browser_checks.json` after the separate UI test is run.

For presentation-only changes, rebuild the HTML without regenerating any data
or re-reading source banks:

```sh
/opt/anaconda3/bin/python3 -B "/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_data_catalog/build_catalog.py" --render-only
```

This writes only `index.html` from `viewer.template.html`, the existing
`catalog.json`, and read-only pipeline source evidence. The 2026-09-05 redesign preserved the catalog data, active loop
and judge manifests, and the target Table 3 CSV. Browser verification covers
all four views at 1440, 390 and 320 pixels, keyboard tabs, dataset/flaw
selection, verbatim source text, historical filters, local links, and offline use.

## Answer Key and Pipeline Evidence

The Answer key & code view explains deterministic flaw construction, the
`balanced_subset()` selection of 20 packet IDs per flaw, and the scorer's
packet-ID join and target-to-flag match. It links all four selected private
truth maps. The Packet explorer displays the exact truth record already
retained in the catalog. Intended targets are not independent human gold
labels, and the quality rubric is not a lookup in that truth map.

The full-file code viewer embeds the current v2 run's frozen loop assets and
quality implementation, prompts, configuration and protocol. The renderer
verifies their SHA-256 hashes against the loop and quality manifests before
writing the page. Four preparation/selection scripts are separately labeled
current source references: these manifests do not establish their historical
executed versions. This is a code-and-provenance snapshot, not a live progress
display or a complete transcript of all model requests. No inference runs,
scoring calls, manifest edits or experiment-result changes occur on rebuild.
