# ICL priority resume

GoEmotions ICL was resumed on 2026-09-12 at the user’s request. The existing frozen protocol and all 5,427 Base predictions are retained. The previously repaired tokenizer return type now produces the seed-42 context-packed prefix with 899 official training demonstrations. No test labels are included in that prefix. Model, context budget, output cap, data splits and evaluation metrics are unchanged.

The CaChe/ParlaMint paired-feedback queue is paused after preserving 10 reference annotations. The original GT-free pilot and Dreaddit remain paused. Only the GoEmotions queue uses the local model. Its existing sequence resumes ICL, then MIPROv2 and GEPA, followed by Conformability judgments. Five-minute monitoring now follows this queue and emphasizes ICL.
