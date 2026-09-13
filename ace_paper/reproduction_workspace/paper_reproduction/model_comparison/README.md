# Local Model Comparison

This is a separate exploratory track. Its outputs are never treated as ACE
paper-reproduction results.

The runner sends the same official ACE Finance Generator prompt to each Ollama
model, using the same benchmark records and decoding settings. It stores raw
responses, extracted answers, exact-match scores, token usage, and latency.

Default comparison:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/compare_local_models.py \
  --task formula --samples 3
```

Choose models explicitly:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/compare_local_models.py \
  --models llama3.1:8b qwen3:8b gemma3:4b deepseek-r1:8b \
  --task finer --samples 3
```

Runs are sequential so a 24GB machine does not try to keep several multi-GB
models resident simultaneously. The completed outputs are still presented in
one side-by-side report.

Precision-guided Formula comparison:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/compare_local_models.py \
  --task formula --samples 3 \
  --playbook paper_reproduction/model_comparison/playbooks/formula_precision_v1.txt
```

`formula_precision_v2.txt` records the benchmark-specific corrections learned
from v1 failures: Operating Margin is returned in percentage points, Dividend
Yield is returned as a decimal ratio, and constant-growth DDM uses
`D1 / (r - g)`. Keeping both versions makes the context update auditable.

Generate an independently learned playbook for each model:

```bash
paper_reproduction/.venv-finance/bin/python \
  paper_reproduction/scripts/run_model_specific_ace.py
```

This starts every model from the same empty structured playbook and uses that
model for all three ACE roles. Outputs are written under
`model_comparison/model_specific_ace/runs/<timestamp>/playbooks/`.

## Full Formula run with local Qwen3

The following uses all released Formula records (500 train, 300 validation,
200 test), five epochs, up to five reflection rounds, and the official
embedding-based bullet analyzer at threshold 0.90:

```bash
paper_reproduction/.venv-finance/bin/python -u \
  paper_reproduction/scripts/run_model_specific_ace.py \
  --models qwen3:8b \
  --train-samples 500 --validation-samples 300 --test-samples 200 \
  --epochs 5 --reflection-rounds 5 --max-tokens 4096 \
  --eval-steps 100 --deduplicate --native-nonthinking \
  --context-window 32768 --playbook-token-budget 12000
```

Run from `ace_paper/`. This is a local model substitution, not a claim to
reproduce the paper's DeepSeek scores. The native Ollama transport explicitly
disables thinking, requests temperature 0 and seed 42, and sets the context
window. Local differences include quantized Qwen3:8b, serial evaluation,
a 32,768-token context, and a 12,000-token playbook budget. The latter is
measured by the upstream tokenizer and is not an exact Qwen token count.
The runner requires at least 5 GiB of free disk before starting. The native
transport stops on critically low disk space to avoid counting log-storage
failures as model prediction errors.

Each run writes `manifest.json` before inference, including data hashes,
model digest, and settings. The official ACE logs and intermediate playbooks
are written while the run executes. `comparison.json` and `comparison.md`
are produced only after completion.

`qwen3_8b_playbook.txt` is the final learned playbook.
`qwen3_8b_selected_playbook.txt` is the validation-selected playbook actually
used for the final test score. Selection does not use test answers.
