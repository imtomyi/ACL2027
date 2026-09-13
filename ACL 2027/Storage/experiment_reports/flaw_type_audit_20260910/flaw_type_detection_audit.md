# Flaw-Type Detection Audit

Post-hoc private diagnostic. No new model calls or rewritten outputs.

Type presence means the locked final issue list names the intended category and its decision establishes a flaw.
These are generator-intended labels, not independently adjudicated truth. Strict P/R/F1 remain unavailable.

| Dataset | Checkpoint | Intended category | Hits / processed | Pending |
| --- | --- | --- | ---: | ---: |
| Dreaddit | E0 | ALL | 0/65 | 15 |
| Dreaddit | E0 | unsupported_inference | 0/16 | 3 |
| Dreaddit | E0 | hidden_source_concentration | 0/10 | 6 |
| Dreaddit | E0 | lost_negative_case | 0/14 | 2 |
| Dreaddit | E0 | contextual_flattening | 0/15 | 1 |
| Dreaddit | E0 | unsupported_abstraction | 0/10 | 3 |
| Dreaddit | E3 | ALL | 0/65 | 15 |
| Dreaddit | E3 | unsupported_inference | 0/16 | 3 |
| Dreaddit | E3 | hidden_source_concentration | 0/10 | 6 |
| Dreaddit | E3 | lost_negative_case | 0/14 | 2 |
| Dreaddit | E3 | contextual_flattening | 0/15 | 1 |
| Dreaddit | E3 | unsupported_abstraction | 0/10 | 3 |
| GoEmotions | E0 | ALL | 0/65 | 15 |
| GoEmotions | E0 | unsupported_inference | 0/13 | 4 |
| GoEmotions | E0 | hidden_source_concentration | 0/13 | 2 |
| GoEmotions | E0 | lost_negative_case | 0/15 | 3 |
| GoEmotions | E0 | contextual_flattening | 0/12 | 2 |
| GoEmotions | E0 | unsupported_abstraction | 0/12 | 4 |
| GoEmotions | E3 | ALL | 0/64 | 16 |
| GoEmotions | E3 | unsupported_inference | 0/13 | 4 |
| GoEmotions | E3 | hidden_source_concentration | 0/13 | 2 |
| GoEmotions | E3 | lost_negative_case | 0/15 | 3 |
| GoEmotions | E3 | contextual_flattening | 0/12 | 2 |
| GoEmotions | E3 | unsupported_abstraction | 0/11 | 5 |
| CaChe | E0 | ALL | 0/64 | 16 |
| CaChe | E0 | unsupported_inference | 0/15 | 1 |
| CaChe | E0 | hidden_source_concentration | 0/15 | 3 |
| CaChe | E0 | lost_negative_case | 0/9 | 6 |
| CaChe | E0 | contextual_flattening | 0/13 | 3 |
| CaChe | E0 | unsupported_abstraction | 0/12 | 3 |
| CaChe | E3 | ALL | 0/64 | 16 |
| CaChe | E3 | unsupported_inference | 0/15 | 1 |
| CaChe | E3 | hidden_source_concentration | 0/15 | 3 |
| CaChe | E3 | lost_negative_case | 0/9 | 6 |
| CaChe | E3 | contextual_flattening | 0/13 | 3 |
| CaChe | E3 | unsupported_abstraction | 0/12 | 3 |
| ParlaMint-GB | E0 | ALL | 0/64 | 16 |
| ParlaMint-GB | E0 | unsupported_inference | 0/12 | 5 |
| ParlaMint-GB | E0 | hidden_source_concentration | 0/12 | 5 |
| ParlaMint-GB | E0 | lost_negative_case | 0/10 | 2 |
| ParlaMint-GB | E0 | contextual_flattening | 0/16 | 2 |
| ParlaMint-GB | E0 | unsupported_abstraction | 0/14 | 2 |
| ParlaMint-GB | E3 | ALL | 0/64 | 16 |
| ParlaMint-GB | E3 | unsupported_inference | 0/12 | 5 |
| ParlaMint-GB | E3 | hidden_source_concentration | 0/12 | 5 |
| ParlaMint-GB | E3 | lost_negative_case | 0/10 | 2 |
| ParlaMint-GB | E3 | contextual_flattening | 0/16 | 2 |
| ParlaMint-GB | E3 | unsupported_abstraction | 0/14 | 2 |

A no_flaw_established decision with an empty issue list cannot be rescued by a positive review-quality judgment.
Unknown/pending gold is not a negative label and does not qualify a headline detection rate.
