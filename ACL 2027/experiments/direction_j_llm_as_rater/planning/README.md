# Prospective sample-size planning

This directory contains text-free design simulations. The scripts must not open
corpus records, generate results, or authorize real-data processing.

`simulate_sample_size.py` evaluates balanced controlled-item counts across the
five failure families. It assumes one matched natural item per controlled item,
three evaluator roles, and the protocol minimum of three independent ratings
per role and item. The statistical target is the item-paired difference between
trained researchers and the expert role aligned with a failure family after
majority aggregation.

The defaults are planning assumptions, not empirical estimates:

- researcher majority-detection probability: 0.55;
- smallest meaningful aligned-expert gain: 0.15;
- item logit standard deviation: 0.85;
- rater logit standard deviation: 0.45;
- median review time: 3 minutes for researchers and 5 minutes for experts; and
- two-sided alpha: 0.05.

Run from the workspace root:

```bash
python3 experiments/direction_j_llm_as_rater/planning/simulate_sample_size.py \
  --output experiments/direction_j_llm_as_rater/planning/sample_size_scenarios.csv
```

Before preregistration, replace the detection, variance, cannot-judge,
exclusion, timing, and attrition assumptions with estimates from the approved
Dreaddit pilot. The confirmatory calculation should also incorporate the final
mixed model, multiplicity plan, and noninferiority margin. The CSV is therefore
a feasibility screen, not a final power determination.
