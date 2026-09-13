# GT-free thematic coding pilot

Started following the user request to proceed without ground-truth labels. Both corpora use only real local excerpts. Each corpus has 100 unlabeled offline adaptation excerpts and 200 evaluation excerpts, sampled before inference; this is not a full-corpus run. Source-session splits are disjoint. CaChe uses the existing participant-turn eligibility rule. ParlaMint uses 30–800-word turns from the complete local archive. Provisional codebooks are frozen in frozen_config.json; they are not original human labels or the CAP benchmark.

## Methods

Base Qwen3-8B, ACE offline without GT, DC cumulative online without GT, and ACE online without GT. ACE reuses official no-GT prompts and playbook ADD/counter utilities in a custom local checkpointed loop. One epoch, one reflection and curation per adaptation item, no labeled feedback, no validation selection or deduplication analyzer. Offline playbook is frozen for evaluation. Online output is saved before memory updates. Invalid/over-budget ACE operations retain prior memory and are logged. This is a method transfer, not an exact replication of the finance paper.

## Metrics and order

ACC and F1 are unavailable without reference labels. Conformability uses the existing four-criterion source-grounding rubric adapted to thematic coding; it is same-family LLM assessment, not human verification. Judge results never feed adaptation. Each method/corpus prediction run is followed by its audit. Order: both Base runs, both ACE offline runs, both DC online runs, both ACE online runs. Final percentages require all 200 judgments and zero unresolved cases. RESULTS.md links to the automatically updated METRICS.md.

## Local operation

All calls go to local Ollama, Qwen3:8b, thinking disabled. Source text, responses and playbooks remain in local private artifacts. Resume with the same runner and frozen configuration; per-call caches and per-item checkpoints preserve completed inference. The 5-minute monitor reads metadata only. Existing GoEmotions and Dreaddit queues are paused while this pilot has priority. GoEmotions Base results are preserved; its ICL token-counting bug was repaired with an explicit source/configuration amendment.
