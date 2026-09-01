# AMI source-balance internal results

These are real-corpus, local-only exploratory results. They do not measure
human qualitative validity and do not populate the WarrantRoute result tables.

## Classification results

| Scope | Condition | Macro F1 [95% component bootstrap] | Accuracy [95% component bootstrap] |
|---|---|---:|---:|
| official_k10_cv | majority | 0.124 [0.099, 0.146] | 0.246 [0.231, 0.256] |
| official_k10_cv | dominant_role_tfidf | 0.949 [0.900, 0.983] | 0.949 [0.899, 0.991] |
| official_k10_cv | pooled_tfidf | 0.992 [0.975, 1.000] | 0.992 [0.974, 1.000] |
| official_k10_cv | role_balanced_tfidf | 0.992 [0.975, 1.000] | 0.992 [0.974, 1.000] |
| official_unseen | majority | 0.100 [0.100, 0.100] | 0.250 [0.250, 0.250] |
| official_unseen | dominant_role_tfidf | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| official_unseen | pooled_tfidf | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |
| official_unseen | role_balanced_tfidf | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] |

## Prespecified comparisons

- Pooled minus dominant-role macro F1 in official k10 CV: 0.043 [0.009, 0.079]. H1 supported: yes.
- Role-balanced minus pooled macro F1 in official k10 CV: 0.000 [0.000, 0.000]. H2 noninferiority at -0.05 supported: yes.

## Source concentration

Across 138 meetings, the median largest-role word share was 0.377 (IQR 0.323–0.443). The median normalized four-role HHI was 0.045.

## Interpretation limits

The task predicts an elicited scenario phase from lexical content. It does not
show that a model produced a valid theme, preserved participant voice, detected
a serious error, routed expertise correctly, or repaired an interpretation.
The official-unseen sensitivity set contains only five connected components, so
its interval is descriptive. No transcript terms or examples were inspected or
selected for this report.
