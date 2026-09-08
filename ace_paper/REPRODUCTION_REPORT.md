# ACE Mechanism Reproduction Report

## Claim boundary

This is a mechanism-level reproduction of ACE, not a replication of a headline
paper metric. It uses the official implementation and real released Formula
records, but only a deterministic 2-train/2-validation/2-test subset and a local
`qwen3:8b` model.

## Fixed inputs

- Official repository: `https://github.com/ace-agent/ace`
- Official commit: `82709de050e1db6e6ef2f07bcb0393560b94992a`
- Model: Ollama `qwen3:8b`
- Model digest: `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`
- Data: first two records of each official Formula train, validation, and test file
- Ground-truth reflection: enabled
- Reflection rounds: one
- Curator frequency: every training sample
- Embedding-based bullet analyzer: disabled

Full source and derived-subset hashes are recorded in `PROVENANCE.json` and
`reproduction/data/manifest.json`.

## Observed execution

1. Initial test: 2/2 correct (accuracy 1.0).
2. Training record 1 (Current Ratio): initially correct. Reflector analyzed the
   success and Curator added `calc-00001`.
3. Training record 2 (ROI): initially incorrect. One reflection round corrected
   the answer, and Curator added `calc-00002`.
4. Validation with the evolved playbook: 2/2 correct (accuracy 1.0).
5. Final test with the selected playbook: 1/2 correct (accuracy 0.5).

The verifier found logs for Generator, Reflector, and Curator, two valid `ADD`
operations, two structured bullets, all required result files, and an unmodified
official checkout.

## Evolved playbook

```text
[calc-00001] helpful=1 harmful=0 :: Current Ratio = Current Assets / Current Liabilities. Always format the result as a floating point number, rounding to two decimal places if required.
[calc-00002] helpful=0 harmful=0 :: Return on Investment (ROI) = Net Profit / Total Investment. Always format the result as a floating-point decimal (e.g., 0.2) without percentage symbols or x100 conversion.
```

This demonstrates the central ACE mechanism: an execution is evaluated, a
reflection is produced, the Curator emits a delta, and deterministic code merges
that delta into persistent context used by later executions.

## Negative-transfer observation

The final error was on Operating Margin. The expected answer was `15.0`, but the
model returned `0.15`. The final prompt contained `calc-00002`, whose ROI-specific
instruction says not to apply an `x100` conversion. The model then omitted the
explicit `x100` in the Operating Margin formula.

This is consistent with negative transfer from an over-applied playbook item. It
is not proof of causation and is not a statistically meaningful performance
estimate: the test has only two records, and local generation can vary. It does,
however, show why playbook quality, retrieval or bullet selection, and harmful
usage tracking matter in addition to merely accumulating context.

## Re-run and verification

```bash
cd /Users/tom/Documents/GitHub/ACL2027/ace_paper
.venv/bin/python reproduction/run_smoke.py
.venv/bin/python reproduction/verify_run.py
```

The complete verified run is under
`results/ace_run_20260904_205609_formula_local_smoke_offline/`.

