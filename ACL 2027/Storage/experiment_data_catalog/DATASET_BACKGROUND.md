# Dataset Background

## Dreaddit

**Version:** Author archive retrieved August 25, 2026. The source manifest does not specify a numbered release.

**Split:** Official `dreaddit-train.csv`, prepared as `development_train`. The official test split is excluded from this n100 sample.

**Source:** [Version, split and file hashes](../../dataset/manifests/dreaddit_source_manifest.json).

## GoEmotions

**Version:** Google Research's simplified release, retrieved August 29, 2026 and hash-verified September 1. No numbered version is recorded.

**Split:** Official simplified `train.tsv`, prepared as `development_train`. The official dev/test splits and full-dataset CSVs are excluded.

**Source:** [Release, split and file hashes](../../dataset/proposals/goemotions_parlamint_swap/provenance_goemotions.md).

## CaChe

**Version:** Source deposit version 1 (2024), DOI `10.25417/uic.26495884.v1`.

**Split:** Participant turns from the prepared records. The stored project label is `heldout_cross_domain_evaluation`; it is not an official source split or an assurance that these previously used records remain unseen.

**Source:** [Version and source files](../../dataset/manifests/agyw_source_manifest.json).

## ParlaMint-GB

**Version:** British component of ParlaMint 3.0, archive `ParlaMint-GB.tgz`, retrieved September 1, 2026.

**Split:** Sampled speaker turns from the British archive. The stored project label is `heldout_cross_domain_descriptive`, not an official train/test split.

**Source:** [Archive version and hash](../../dataset/proposals/goemotions_parlamint_swap/provenance_parlamint_gb.md).

## Experiment details

### Data size and unit

This section describes the catalog's Table 3 n100 sample and historical baseline reviews. The September 5 same-model WarrantRoute protocol is identified separately below; later playbook pilots are not pooled into these counts.

| Dataset | Source collection counted locally | Builder-eligible records | Prepared packets | Evaluated n100 packets |
|---|---|---:|---:|---:|
| Dreaddit | 3,553 segments: 2,838 train + 715 test | 2,817 train segments | 580 | 100 |
| GoEmotions | 54,263 simplified comments: 43,410 train + 5,426 dev + 5,427 test | 38,160 train comments | 9,540 | 100 |
| CaChe | 11 transcript files; unfiltered participant-turn total not verified here | 3,076 prepared turns | 765 | 100 |
| ParlaMint-GB | 670,912 speaker turns in the local British archive | 607,907 turns | 100 | 100 |

These eligible counts describe the historical packet builders, not universal eligibility or processing clearance. Source units differ across datasets. GoEmotions counts concern the simplified release, not its larger full annotation collection.

**One evaluation sample = one packet:** four source excerpts + one constructed claim + a research question and metadata. It is not one original document or one participant.

**Excerpt 1-4:** the four source passages included in one packet. Each passage is a Reddit segment/comment, a focus-group turn, or a parliamentary turn, depending on the dataset. Numbering restarts in every packet: repeated "Excerpt 1" labels do not mean the text is identical. The number indicates position, not importance or the answer. **Cited** means the claim references that passage; **Context** means it was supplied to the reviewer but not cited by the claim. The four passages need not belong to the same conversation.

**Why four excerpts?** Four is a fixed construction choice in the historical builders, not an established optimal sample size. The implementation supports three practical considerations:

- **Compare evidence:** the claim usually cites excerpts 1 and 2, leaving 3 and 4 available for checking omitted evidence or contextual differences. The source-concentration template cites only excerpt 1. Uncited passages are not automatically counterevidence.
- **Keep input structure consistent:** every dataset and condition uses the same number of excerpts, although their word counts differ.
- **Limit context size:** the ParlaMint builder explicitly caps turns at 800 words to keep four-excerpt packets within the local 8,192-token context budget. This explains its length filter, not why four would outperform another excerpt count.

The inspected construction records do not document a comparison of two, four and six excerpts. Four should therefore be reported as a design setting, not a validated optimum. Sources: [claim and packet construction](../../experiments/rq2_role_prompted_llm/scripts/build_working_dreaddit_packet_bank.py), [multicorpus construction](../../experiments/rq2_role_prompted_llm/scripts/build_working_multicorpus_packet_banks.py), [context-budget rule](../../experiments/rq2_role_prompted_llm/scripts/build_parlamint_full_sample_bank.py).

**n100 = 100 packets per dataset:** 400 packets and 1,600 excerpt occurrences overall. Each dataset contributes 400 distinct source records. The CaChe records span 11 transcript files; ParlaMint-GB spans 352 session source IDs.

| Dataset | n100 share of its prepared packet bank |
|---|---:|
| Dreaddit | 100 / 580 = 17.24% |
| GoEmotions | 100 / 9,540 = 1.05% |
| CaChe | 100 / 765 = 13.07% |
| ParlaMint-GB | 100 / 100 = 100% |

These percentages compare packets with packets. They are not percentages of the original corpus or all historical executions. Earlier runs are listed separately in the [inventory](inventory.html).

Sources: [Dreaddit bank](../draft_review_packets/dreaddit_dev580_working_v1/manifest.json), [GoEmotions bank](../draft_review_packets/goemotions_train_all_working_v1/manifest.json), [CaChe bank](../draft_review_packets/agyw_focus_groups_eval765_working_v1/manifest.json), [ParlaMint-GB bank](../draft_review_packets/parlamint_gb_fullsample_eval100_working_v1/manifest.json), [catalog audit](audit.json). Source collection totals come from the dataset records linked above.

### Shared inputs across conditions

Qwen3 8B, Llama 3.1 8B and Gemma 3 4B use the same 400 packet IDs, claims and source excerpts. Baseline prompts are identical across models within each role after the recorded prompt-identity repair.

| Method | Reviews used for each packet and model |
|---|---|
| Generalist | Generalist review |
| Fixed role | Qualitative-methods review |
| All roles | Generalist + qualitative-methods + domain reviews |
| WarrantRoute, September 5 same-model protocol | One loop trajectory using the same packet; every loop role uses the selected model |

All roles reuses the stored role reviews. It does not draw another sample. The same-model WarrantRoute protocol also fixes role instructions and packet IDs across the three model conditions.

Sources: [Baseline identity audit](../draft_review_packets/table3_n100_prompt_identity_repair_v1_final.json), [packet bindings](audit.json), [same-model protocol](../rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2/quality/protocol.md).

### Five intended flaws

**Flaw:** a located, material failure of the relationship between an analysis claim and its supplied evidence. The object being judged is the interpretation, not the source participant.

Establish a flaw only when the affected claim is identifiable, a specific evidential problem can be explained, and correcting it would change the meaning, scope, attribution or disposition. Different wording or another defensible interpretation is not enough.

| Type | Required problem | Not sufficient |
|---|---|---|
| Unsupported evidence | A material assertion or citation lacks the inferential support it claims. | A different opinion or not citing every excerpt. |
| Source concentration | Narrow source support is presented as warranting a broader or representative claim. | One citation, when the conclusion is limited to that source. |
| Counterevidence loss | A consequential countercase or qualification is omitted from the conclusion. | An uncited or unrelated passage, or an exception already acknowledged. |
| Contextual flattening | A meaningful local distinction is collapsed, changing the interpretation. | Shortening text or omitting irrelevant metadata. |
| Unsupported abstraction | A theoretical concept, scope or strength exceeds what the passages warrant. | Abstract terminology or a theme that uses new words. |

Use the most specific evidenced mechanism. Do not double-count one problem under a generic category; independently evidenced defects may coexist. Missing essential context leads to **Cannot judge**, not an assumed flaw. Lack of support does not prove the opposite claim.

**Historical measurement:** n100 assigns 20 packets per intended flaw per dataset. The scorer checks whether the mapped target flag occurs in the review; All roles uses the union of role flags. It does not verify that the rationale or highlighted passage actually establishes the defect. The labels remain construction targets.

**Version distinction:** historical unsupported-abstraction templates emphasize theoretical overinterpretation. Later six-excerpt construction rules also cover excess scope or strength. This consolidated explanation does not retroactively change either run's scoring.

[Full criteria, exceptions and experiment audit](../experiment_guidelines/flaw_criteria_audit_v1.md). Based on the [shared rater guide](../../experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md), [existing prospective criteria](../experiment_guidelines/objective_review_criteria_v1.md), and [historical scorer](../../experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py).

### Executions and retries

| Stage | Count per unit | Handling |
|---|---|---|
| Baseline review | One accepted output per packet-role-model; 3,600 retained outputs | Historical attempts may exceed one. The identity repair regenerated 229 outputs, not 229 new samples. |
| Baseline quality judge | One primary judgment per packet-method-model; 3,600 logical evaluations | Each response provides both Credibility and Conformability. Scheduled primary repeats: 0. |
| Same-model WarrantRoute protocol | One trajectory per packet-model; 1,200 planned trajectories | Internal role calls and up to two revision rounds are part of that trajectory, with a 12-call cap. |
| WarrantRoute quality judge | One logical judgment per assessable trajectory | Both quality dimensions come from the same judgment. |

For quality judging, transport or invalid-format failures permit up to two additional technical attempts, three in total. Keep the first valid response and preserve failed attempts. Valid false/null judgments are not retried to improve scores. Missing or unresolved judgments are retained in the accounting; they are not additional samples or silently dropped.

For the frozen same-model loop, completed trajectories are reused on resume, and failed/in-flight calls are not recreated under a new identity. Human escalation is a terminal outcome, not automatically a technical failure. A later recovery run requires its own recorded contract.

One retained result does not prove that only one HTTP request occurred. Planned repetitions, technical retries and historical replacements are separate quantities. The source logs, rather than file totals, are needed for an exact attempt count.

Sources: [Baseline quality execution rules](../draft_review_packets/table3_review_quality_v1/README.md), [229-output repair audit](../draft_review_packets/table3_n100_prompt_identity_repair_v1_final.json), [same-model execution protocol](../rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2/quality/protocol.md).
