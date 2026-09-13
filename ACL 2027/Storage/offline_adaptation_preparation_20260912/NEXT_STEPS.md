# Offline adaptation preparation

Status: proposed protocol, not experimental evidence. Existing Dreaddit runs are checkpointed and paused. No new dataset inference has started.

## Immediate candidate: GoEmotions

Use the official simplified labels (27 emotions plus neutral), keeping multilabel annotations. Proposed task: predict the full emotion label set and a brief source-grounded rationale. Proposed ACC definition: exact set match, alongside micro/macro F1 to avoid hiding partial correctness. This is distinct from Dreaddit binary stress accuracy. Do not aggregate their raw accuracies into a common-task claim. Use official train/dev/test roles and freeze all settings before test inference. Baseline, ICL, official DSPy MIPROv2 and GEPA can be adapted to this signature. ACE remains a separately scoped implementation.

## CaChe and ParlaMint-GB

The current local catalog does not identify adjudicated gold labels for the proposed accuracy task. Historical packet flaw labels are not established human reference labels for natural model outputs. Do not use generated or injected labels as manuscript evidence or treat model agreement as GT.

Recommended pilot: define corpus-specific qualitative codebooks using development excerpts, then have two people independently code held-out real excerpts and adjudicate differences. Record labels, supporting text spans and insufficient-context cases. Split CaChe by focus-group/session and ParlaMint by debate/session, considering speaker overlap, before optimizer access. Choose sample sizes after inspecting label support. Keep evaluation annotations hidden from offline adaptation.

Alternative shared task: judge whether a naturally generated qualitative claim is supported by its supplied excerpts, with independently adjudicated human reference judgments. This aligns evidence-grounding comparisons across corpora but constitutes a new task and cannot reuse the current stress-classification ACC as its result.

## Decision needed

Choose between native classification tasks and a shared qualitative support/coding task before filling missing ACC cells. GoEmotions native classification can proceed independently once its metric definition is accepted. Conformability alone is a secondary judge-based metric and does not supply GT for supervised adaptation.
