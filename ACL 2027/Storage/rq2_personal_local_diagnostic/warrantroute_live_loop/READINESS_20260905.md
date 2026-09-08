# WarrantRoute n=100 Readiness Record

Date: 2026-09-05

## Later User-Requested Same-Model Run

The record below describes the earlier mixed-family preparation, which was not
launched. The later requested comparison uses one model for every agent within
each condition. Its active run is
[n100_same_model_table3_20260905_v2](n100_same_model_table3_20260905_v2/README.md).
It freezes a separate same-model policy and secondary Credibility/Conformability
measurement. Consult its manifest and live progress, not the old launch command
below. The historical v2 bundle was not rewritten after the explicit same-model
extension changed implementation hashes.

## Historical Mixed-Family Readiness

Status: prepared for private working execution. The full experiment has not
been launched. This record does not establish manuscript eligibility or
semantic repair quality.

## Launch Bundle

Use [n100_ready_20260905_v2/manifest.json](n100_ready_20260905_v2/manifest.json).
It freezes the current implementation, prompts, policy, model digests, seeds
and packet snapshots. The three assignments are `qwen_led`, `llama_led` and
`gemma_led`, using Qwen3 8B, Llama 3.1 8B and Gemma 3 4B.

| Dataset | Unique packets | Matched answer-sheet IDs |
| --- | ---: | ---: |
| Dreaddit | 100 | 100 |
| GoEmotions | 100 | 100 |
| CaChe | 100 | 100 |
| ParlaMint-GB | 100 | 100 |

The planned inventory is 400 unique packets, three mixed-model assignments,
one repetition and the `warrantroute` condition: 1,200 trajectories. The cap
is 12 calls per trajectory, or 14,400 calls overall. This is a budget bound,
not an expected cost. At preparation, completed trajectories and model calls
are both zero.

From the project directory, launch or resume with:

```sh
cd "/Users/tom/Documents/GitHub/ACL2027/ACL 2027"
/opt/anaconda3/bin/python3 -B \
  experiments/rq2_role_prompted_llm/scripts/run_warrantroute_loop_n100.py \
  run --run-dir Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_ready_20260905_v2
```

The [experiment guide](../../../experiments/rq2_role_prompted_llm/WARRANTROUTE_LOOP_EXPERIMENT_GUIDE.md)
documents progress, scoring, alternate configurations and the comparison
protocol. Add `--max-packets 3` to stop after three additional trajectories.

## Verification

- 18 live-loop contract and pipeline tests passed.
- 34 existing WarrantLoop/WarrantRoute replay regression tests passed.
- 10 ACE controller tests passed. Total: 62 passing tests.
- All four full input banks have 100 unique packet IDs and matching answer IDs.
  Answer labels are not supplied to the agents or the router.
- Exact installed model digests were verified. Generation uses the local
  Ollama service, not a cloud provider or Portkey.
- Syntax, JSON and targeted whitespace checks passed.

### Live Qualification

The following are engineering checks, not estimates of model quality:

| Run | Coverage | Outcome |
| --- | --- | --- |
| `qualification_20260905_v5` | One Dreaddit packet, all three assignments, all initial agents | Qwen-led and Llama-led completed two revision rounds without execution errors. Gemma-led was quarantined for an inconsistent disposition/expertise pair. |
| `qualification_20260905_v6` | Same development packet, Gemma-led, after output-schema correction | 12 calls and two revision rounds completed without execution errors. Unresolved disagreement led to human escalation. |
| `four_corpus_input_smoke_20260905_v2` | One packet from each dataset, Qwen-led routed initial audits, revision disabled | Four trajectories and eight calls completed without errors. Each stopped at human escalation with revision disabled. |

The v6 correction encodes compatible disposition/expertise combinations in
the generation schema. It does not normalize away contradictory outputs or
relax issue ownership. The earlier Qwen-led and Llama-led full trajectories
used the predecessor schema and are not presented as a complete rerun under
the final schema. The final-code checks exercise all three model families,
the full Gemma-led revision path and the four Qwen-led input paths.

Scoring completed for these runs. Resume was tested after completion and
generated no additional calls. The corrected v6 run and four-corpus smoke
retained 12 and eight calls respectively. Small-sample recall exports are
private diagnostics and do not support a performance ranking.

Earlier qualification attempts are retained with their failures. The unused
preparations `n100_ready_20260905`, `four_corpus_qualification_20260905` and
`four_corpus_input_smoke_20260905` predate the final schema correction and
were never launched. Their current-code hash checks deliberately fail.
Do not use them instead of the v2 launch bundle.

## Interpretation Limits

The four banks were already exposed during development and include controlled
flaw-template claims. They are not a fresh held-out evaluation and cannot fill
manuscript result cells. The answer sheets identify intended flaws, not every
possible flaw or a gold-standard rewrite.

Human escalation is a valid terminal execution state, not a successful repair.
None of these checks demonstrates that revision improved the document. The
runner leaves independent repair quality unset. An independent qualified
evaluation remains necessary for that claim.

Initial routing uses WarrantGate v0 plus expertise requests. Calibrating a
learned revision-value policy, enabling an outer Playbook-learning loop and
building a formal publication pipeline remain separate work. They are not
implicitly enabled by this launch bundle.
