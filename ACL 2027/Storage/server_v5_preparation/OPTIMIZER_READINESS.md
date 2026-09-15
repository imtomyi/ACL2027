# Remaining optimizer integration

Twelve seed runs remain: MIPROv2 and GEPA on Dreaddit and GoEmotions, seeds 42/43/44. Preserve 100 train and 100 development records, train-only demonstrations, no test selection, the 4096-token learned-context envelope, and shared native runtime/output validation.

Pinned server packages: DSPy 3.0.3 and GEPA 0.0.7. Read-only inspection confirms MIPROv2 constructs `dspy.Evaluate` in `dspy/teleprompt/mipro_optimizer_v2.py`. An aggregate evaluator adapter can select on whole-development Macro-F1 (Dreaddit) or Micro-F1 (GoEmotions), while bootstrap trace acceptance must be recorded separately.

GEPA 0.0.7 `EvaluationBatch.scores` is a per-item list. Its engine sums scores for minibatch acceptance and takes their arithmetic mean for full validation selection and Pareto fronts. `gepa/core/state.py` initializes full score with `sum(scores)/len(scores)`. Passing per-item exact-match scores does not implement either registered F1 objective. There is no aggregate callback in the inspected `gepa.optimize` signature. Do not claim a straightforward DSPy per-item metric is the fixed global F1 objective. Any batch contribution decomposition or change to score aggregation needs explicit mathematical validation and method-transfer documentation, especially its effect on Pareto selection and perfect-score skipping.

These findings are preparation notes, not evidence that either optimizer has run. Inspect the pinned APIs and test actual optimizer behavior before sealing another stage. Do not change the running Base/ICL or ACE/DC seals.
