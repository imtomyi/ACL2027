# GoEmotions offline comparison

This local diagnostic transfers official DSPy MIPROv2 and GEPA to multilabel emotion classification. It is not an exact reproduction of the ACE finance benchmark. The serial queue runs Base, ICL, MIPROv2 and GEPA, then independently judges their explanations for Conformability.

The original simplified release is used: 43,410 training, 5,426 development and 5,427 test comments. Training and development labels support offline adaptation. Test labels are accessed only by scoring. Comment IDs are disjoint across splits; this does not establish author separation or exclude identical text across splits.

ACC is exact label-set match, independent of label ordering. Micro-F1 pools label decisions; macro-F1 averages all 28 label scores with zero-division set to zero. Invalid outputs receive incorrect ACC and an empty predicted label set for F1. Final scores are written only after all test examples complete.

Inference uses local Ollama Qwen3-8B Q4_K_M, thinking disabled, a 32,768-token context and seed 42. Base and ICL request a structured brief rationale and emotion IDs with a 512-token output cap. ICL uses a seed-42 shuffled fixed training prefix packed into context. Official DSPy optimizers use heavy mode, one worker, all available training/development records and a 4,096-token output cap. The rationale format and optimizer-selected prompts differ between methods and should be disclosed.

Conformability reuses the local evidence-grounding rubric adapted to emotion labels. The judge receives only the passage and anonymous answer, without reference labels, method identity or adaptation context. No judgment reaches optimization. This is a same-family LLM pass rate, not an independent human assessment. A final percentage requires all 5,427 judgments with zero unresolved cases.

Run artifacts are under `ACL 2027/Storage/goemotions_offline/run_20260912`. `predictions.jsonl` and `quality.jsonl` checkpoint each item; state files track progress; optimizer response caches support resumption. Raw local model responses may contain corpus excerpts and should not be published unreviewed. Frozen configuration, source hashes, official split IDs and implementation snapshots are retained. Interrupted incomplete final JSONL appends are preserved separately before recovery; malformed committed rows cause a failure.

To resume, use the existing `ACL 2027/Storage/dreaddit_icl/runtime313/bin/python` executable with this directory's `run.py`. The queue lock prevents duplicate runners. Do not resolve the Python executable symlink out of its virtual environment. Keep Dreaddit paused while this queue uses the model.

`test_contracts.py` uses software fixtures only and verifies exact-match/F1 denominators, invalid label handling, checkpoint recovery and judge payload boundaries. Fixture values are never experiment evidence.
