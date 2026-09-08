# Flaw Definition and Experiment Audit

Version: 1.0. Date: 2026-09-09 KST.

Status: consolidated explanation and prospective annotation specification. Historical results retain their frozen definitions and scoring. This document does not launch inference, relabel packets, or implement a new scorer.

## 1. Common definition

A flaw is a located, material failure of the relationship between an analysis claim and the evidence supplied for its review.

The object being assessed is the interpretation, not the source participant's experience, honesty, writing quality, diagnosis, or emotions. A claim need not be the only defensible interpretation.

All three conditions are required for an established flaw:

1. **Identifiable target:** specify the affected assertion, attribution, scope, or omitted qualification.
2. **Demonstrable evidential problem:** locate relevant supplied evidence and explain the missing support, contradiction, misrepresentation, or unjustified extension. A construction label or model vote is not this explanation.
3. **Material consequence:** correcting the problem would change the substantive interpretation, attribution, claim strength, scope, recommended action, or disposition. Cosmetic rewriting does not qualify.

For unsupported assertions, explain the missing inferential link after considering the available packet. Absence of support can establish that the assertion is unwarranted within this packet; it does not establish that the opposite is true in the world.

## 2. Type-specific decisions

Apply the common definition first, then the type-specific conditions. Do not infer defects from the dataset name, assigned role, or expected answer.

| Family / historical flag | Establish a flaw when | Do not flag solely because |
|---|---|---|
| Unsupported evidence / unsupported_inference | A material assertion lacks the support it claims: identify the proposition and the failed citation or missing inference. Specify whether the issue concerns a fact, relation, causal assertion, or other substantive step. | The interpretation uses different wording, lacks a quotation, or has not cited every excerpt. |
| Source concentration / hidden_source_concentration | A conclusion claims coverage beyond the source units that actually support it, while presenting that narrow support as broader or representative. Identify the supporting units and the overextended scope. | There is only one citation. A conclusion explicitly limited to that source can be warranted. Multiple excerpts can also come from one source. |
| Counterevidence loss / lost_negative_case | A supplied passage contradicts or materially qualifies the claim under relevant conditions, and the claim omits or neutralizes that consequence. Identify the countercase and the qualification required. | An excerpt is uncited, unrelated, merely different, or already accommodated by the claim. |
| Contextual flattening / contextual_flattening | A consequential distinction in speaker position, conditions, time, uncertainty, or local meaning is collapsed, changing the interpretation. Identify the distinction and its effect. | Metadata is omitted, text is shortened, or differences irrelevant to the stated claim are absent. |
| Unsupported abstraction / unsupported_abstraction | The interpretation makes an unwarranted move from the passages to a higher-level theme, explanatory concept, or broader/stronger conclusion. Identify the evidence-to-concept link or scope boundary that fails. | The theme is abstract, uses scholarly language, or does not repeat source vocabulary. |

### Overlap rules

- Use unsupported evidence for a specifically unsupported proposition or citation relation.
- Use source concentration when the decisive problem is representation beyond the supporting source units.
- Use counterevidence loss when an omitted contradictory or qualifying case changes the conclusion.
- Use contextual flattening when a consequential local distinction is collapsed without being primarily a countercase.
- Use unsupported abstraction for an unjustified conceptual or aggregate scope/strength jump.
- Do not count the same problem again under a generic category solely because it is also "unsupported." Multiple categories are appropriate when independently evidenced defects coexist. Record the relationship between overlapping allegations.
- Quotation fabrication, wrong attribution, sensitive/diagnostic inference, codebook inconsistency and other material problems remain available under the wider rater taxonomy. They are not forced into the five constructed target families.

### Decision states

| State | Rule |
|---|---|
| Established flaw | All three common conditions and the category conditions are met. |
| No flaw established | Adequate evidence does not establish the alleged defect, or a countercondition defeats it. This is bounded to the supplied item. |
| Cannot judge | Essential context or expertise is missing and prevents a responsible decision. Do not force a positive or negative label. |
| Technical failure | Missing, invalid or incomplete input/output prevents assessment. This is not a semantic judgment. |

These states describe the assessment of a proposed claim defect. They must not be confused with whether a review allegation is itself supported, contradicted, or insufficiently grounded under the existing review-quality guideline.

## 3. Required annotation

For each prospective allegation, retain:

- Packet ID, claim version/hash and relevant claim field.
- Exact claim span, or the field where a necessary qualification is absent.
- Evidence record/excerpt IDs and exact evidence spans when locatable.
- Category, decision state and concise evidence-to-claim explanation.
- Why the consequence is material, and the smallest correction needed.
- Contrary evidence considered, unavailable context, and any overlapping issue.

Use the offset convention already specified in objective_review_criteria_v1.md: zero-based Unicode code points, inclusive start and exclusive end, with exact stored-text matching. An omitted qualification has no literal span to highlight; identify the affected claim field and supporting countercase instead. Missing spans remain unavailable.

Existing citation IDs may support excerpt-level highlighting. A citation, builder-linked context ID, or reviewer-supplied evidence ID is not automatically a validated answer span.

## 4. What the existing experiment actually does

### Historical four-excerpt n100

The deterministic builders group four excerpts and instantiate one of five intended targets. All 400 cataloged main packets have four excerpts and one target label, with 80 packets per target across the four datasets.

The truth map records what the builder intended. It does not by itself demonstrate that the target is present, that only one flaw exists, or that the remaining text is correct. The templates do not semantically verify every source/claim pairing.

The v1 reviewer prompts and shared guide already require located, material problems, permit empty flags, and distinguish uncertainty from error. They use free-text rationales rather than a required issue-level span annotation.

The historical scorer maps target families to reviewer flags and tests membership. All roles uses the union of role flags: a flag from any included role can satisfy detection. The scorer does not semantically adjudicate the rationale, require a correct span, or subtract other flags from the target hit.

Consequently, flagging all five target categories could achieve full intended-target recall without demonstrating selective or accurate diagnosis. That is a limitation of the endpoint, not permission to use that strategy.

### WarrantRoute loop

The inspected loop runtime requires each issue to have an allowed flag, at least one evidence ID, a diagnosis and a requested change. Validation checks that IDs exist and flags correspond to issue records. Accepting an item with serious issues or sub-4 ratings is rejected by the validator.

These checks strengthen structural traceability, but an existing ID does not prove that its text supports the diagnosis. The loop scorer still uses original detected flags for intended-target recall. Loop acceptance, issue-owner resolution and human escalation do not independently establish repair success.

### Later construction verification

The later v2/v2.1/v2.2 construction prompts use six evidence positions, admissible bases and target-blind comparisons. They are a separate design, not evidence that the historical four-excerpt n100 passed those gates.

There is definition drift: historical unsupported-abstraction templates emphasize theoretical overinterpretation; the later comparison prompt defines it more broadly as excess scope or strength. The later comparison also uses a narrower bad-citation definition for unsupported evidence and routes some causal/diagnostic overreach to other_material_flaw.

The consolidated criteria above expose those mechanisms but do not silently change either implementation. A future executable taxonomy must freeze the exact boundaries and matching rules before generating or scoring new outputs.

### Review-quality judging

Credibility and Conformability concern the review's diagnosis and grounding. A matching target flag is neither necessary nor sufficient for passing these review-quality criteria. A review may flag the intended category yet invent its supporting reason.

Their judge decisions are separate from the three 1-5 first-stage ratings, construction verification, and independent revision assessment.

## 5. Structural audit findings

Scope: the catalog's 400 main n100 packets, their truth records, and all 3,600 linked current baseline output files. Also inspected: historical/v2 prompts, builders, construction schemas, shared rater guide, baseline and loop detection code, loop validation, review-quality protocols, Direction H protocol boundaries, and the September 7 prospective criteria.

| Check | Observed |
|---|---:|
| Main packets | 400 |
| Packets with exactly four excerpts | 400 |
| Packet ID and target consistent with its truth record | 400 |
| Packets per intended target across datasets | 80 |
| Truth records containing sentence/span location fields | 0 |
| Packets with an explicit EXC reference in construction boundary notes | 80 |
| Packets retaining theme_name, explanation and boundary_conditions in the stored claim | 400 |
| Linked baseline output files read | 3,600 |
| Files marked status=valid | 3,600 |
| Parsed ratings with nonempty rationales | 3,600 |
| Parsed ratings with an explicit issues array | 0 |
| Rationales containing an EXC-style reference | 1,122 |

The last count is a literal identifier-pattern check, not a location-accuracy or semantic-quality score. Other rationales may use another reference convention. No packet was semantically relabeled in this audit.

The presence of construction hints in stored claims is consistent with the historical payload limitation already documented by the catalog: its historical sanitizer removed top-level target fields while retaining nested claim hints. Prompt identity and valid JSON do not establish blindness or correctness.

## 6. Application and remaining work

Use this document to explain what qualifies as a flaw and to specify prospective evidence annotations. Preserve existing Table 3 counts, truth maps, prompts, hashes and outputs.

Before a future run claims evidence-grounded flaw detection rather than historical target matching:

1. Freeze a single taxonomy version and resolve the noted category drift.
2. Freeze claim/evidence boundaries and remove target-derived hints from reviewer-visible input.
3. Implement and test annotation identity, exact-span checks and unknown handling.
4. Assess each allegation against the semantic criteria; keep mechanical checks distinct from judge assessments.
5. Establish an appropriate reference design before reporting precision/recall/F1 as natural-flaw detection. Under the already proposed no-human diagnostic, report bounded judge-assessed outcomes without calling model consensus ground truth.
6. Keep original diagnosis, review quality and revised-claim quality as separate endpoints.

These are remaining implementation/evaluation tasks, not checks passed by writing this document. The inspected files do not supply a validated, complete natural-flaw reference inventory for these 400 packets.

## 7. Source map

- [Existing prospective criteria](objective_review_criteria_v1.md)
- [Shared rater guide](../../experiments/direction_j_llm_as_rater/protocol/shared_rater_guide_v1.md)
- [Historical generalist prompt](../../experiments/rq2_role_prompted_llm/prompts/generalist_v1.md)
- [Historical prompt identity bindings](../../experiments/rq2_role_prompted_llm/config/table3_n100_prompt_identity_repair_v1.json)
- [Dreaddit construction](../../experiments/rq2_role_prompted_llm/scripts/build_working_dreaddit_packet_bank.py)
- [Multicorpus construction](../../experiments/rq2_role_prompted_llm/scripts/build_working_multicorpus_packet_banks.py)
- [Historical detection scoring](../../experiments/rq2_role_prompted_llm/scripts/score_working_detection_table.py)
- [Loop issue schema and validator](../../experiments/rq2_role_prompted_llm/scripts/warrantroute_loop_runtime.py)
- [Loop detection scoring](../../experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py)
- [Later comparison rules](../../experiments/rq2_role_prompted_llm/prompts/construction_comparison_v2_1.md)
- [Later base-admissibility rules](../../experiments/rq2_role_prompted_llm/prompts/base_admissibility_v2_2.md)
- [Construction verification schema](../../experiments/rq2_role_prompted_llm/schemas/construction_verification.schema.json)
- [Historical review-quality rules](../draft_review_packets/table3_review_quality_v1/README.md)
- [Frozen same-model protocol](../rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2/quality/protocol.md)
- [Catalog inventory](../experiment_data_catalog/audit.json)
- [Direction H protocol](../../experiments/direction_h_human_in_loop/protocol/study_protocol.md)
