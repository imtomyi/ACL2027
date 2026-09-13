# GT-free real-corpus pilot

Pilot: 100 unlabeled adaptation excerpts and 200 evaluation excerpts per corpus. No reference labels: ACC/F1 unavailable. Conformability is same-family LLM grounding assessment, not human validation.

| Corpus | Method | GT | Acc | Conformability % | Progress |
| --- | --- | --- | --- | ---: | --- |
| cache | base | — | N/A | — | running; adapted 0/0; predictions 28/200; judged 0/200; unresolved 0 |
| cache | ace_offline_no_gt | ✗ | N/A | — | queued; adapted 0/100; predictions 0/200; judged 0/200; unresolved 0 |
| cache | dc_online_no_gt | ✗ | N/A | — | queued; adapted 0/0; predictions 0/200; judged 0/200; unresolved 0 |
| cache | ace_online_no_gt | ✗ | N/A | — | queued; adapted 0/0; predictions 0/200; judged 0/200; unresolved 0 |
| parlamint_gb | base | — | N/A | — | queued; adapted 0/0; predictions 0/200; judged 0/200; unresolved 0 |
| parlamint_gb | ace_offline_no_gt | ✗ | N/A | — | queued; adapted 0/100; predictions 0/200; judged 0/200; unresolved 0 |
| parlamint_gb | dc_online_no_gt | ✗ | N/A | — | queued; adapted 0/0; predictions 0/200; judged 0/200; unresolved 0 |
| parlamint_gb | ace_online_no_gt | ✗ | N/A | — | queued; adapted 0/0; predictions 0/200; judged 0/200; unresolved 0 |

Methods are local task transfers; not exact finance-paper reproduction. Online outputs are recorded before updates. No judge outcomes reach adaptation. Source sessions are disjoint for offline adaptation/evaluation; recurring speakers may overlap in ParlaMint. No changes to the existing confirmatory study protocol.
