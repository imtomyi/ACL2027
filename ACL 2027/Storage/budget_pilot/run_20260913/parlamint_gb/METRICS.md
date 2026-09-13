# Paired reference-feedback pilot

Real excerpts; 4 adaptation and 8 evaluation items per corpus. GT ✓† means unverified local Qwen3-8B reference labels are supplied to adaptation. These are pseudo-labels, NOT human ground truth. GT ✗ receives no reference labels. Base receives neither.

Human-GT ACC/F1 are N/A. Reference agreement is exact topic-set agreement with the frozen model annotation, not accuracy. Same-family model bias applies. Conformability is a reference-blind LLM grounding judgment, not human verification.

Reference annotation preparation: 0/12. Sealed: False.

| Corpus | Method | GT labels | Human-GT Acc | Reference agreement % | Conformability % | Progress |
| --- | --- | --- | --- | ---: | ---: | --- |
| ParlaMint-GB | Qwen3-8B | — | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE offline | ✗ | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE offline | ✓† | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | DC online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | DC online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE online | ✗ | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |
| ParlaMint-GB | ACE online | ✓† | N/A | — | — | queued; adapted 0; predictions 0/8; judged 0/8; unresolved 0; invalid topic outputs 0 |

† References are generated once from the source and fixed codebook, with no evaluated answers, playbooks or judge outcomes. All 12 annotations are sealed before comparative prediction. Matching codebook IDs and verbatim evidence checks verify format/traceability only, not semantic correctness.
Offline: feedback only on 4 adaptation items, then freeze memory. Online: label feedback only after the current prediction, affecting future items. Same task, data, order, model, seed and per-call caps across each pair; native official with/no-GT prompt templates differ. Conformability never feeds adaptation.
Local exploratory method transfer with model-generated supervision; keep separate from human-GT benchmark and manuscript results. The earlier GT-free run is preserved separately; structured topic outputs in this protocol require new paired baselines.
