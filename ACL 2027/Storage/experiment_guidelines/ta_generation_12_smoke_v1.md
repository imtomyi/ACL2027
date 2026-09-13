# Twelve-Point TA Generation Smoke Test

Protocol: `ta-generation-smoke-v1`. User-authorized local generation test only.
This implements the construction stage of
[the TA-artifact guideline](ace_ta_artifact_flaw_detection_v1.md), not its entire
flaw-detection, learning or evaluation pipeline.

## Frozen Scope

- Reuse the 12 original Dreaddit development paragraphs from
  `dreaddit_playbook_new12_20260910T083622Z`. They are previously exposed, not a
  new held-out evaluation set. Original text and identities remain unchanged.
- Retain their three existing four-record parent packets and original order.
  One paragraph is one source data point. One packet is one TA analysis item.
- One Gemma 3 4B TA Analyst call per packet: three calls, twelve data points,
  one generation per packet. No epochs, detector, evaluator or Playbook updater.
- Reuse the Dreaddit working-bank research question: "How do people describe
  and contextualize experiences of stress?" The code freezes its provenance.
- Generate semantic codes, optional subthemes and provisional packet-local
  themes with evidence. Do not force themes, code counts or a hierarchy.
- Supply source text and source identities only, not constructed claims, stress
  labels, flaw keys, previous reviews, Playbook rules or quality scores.
- Preserve participant context and uncertainty. These short excerpts do not
  support population-level conclusions, diagnoses or saturation claims.
- Source text can include sensitive autobiographical material. Keep all outputs
  local under private Storage. Prior exclusions and publication limitations
  remain; this run is not a privacy clearance or manuscript-qualified study.

## Execution and Validation

Pin the installed model digest inherited from the source run. Use temperature 0,
the inherited seed and 32,768-token context, with an 8,192-token output ceiling.
Admit each complete input and schema conservatively before inference. No silent
source truncation, semantic retries, output rewriting or selecting a favorable
generation. The hard ceiling is three local calls and twenty minutes, with a
five-minute timeout per call. A timeout is uncertain completion and requires
inspection, not automatic retry. No downloads or paid calls are permitted.

Acquire the existing shared inference lock and a per-run lock. Start a local
Ollama server only if needed and clean up only that owned server. Frozen source,
code, prompt, schema and request hashes bind every output. Keep exact raw
responses even when invalid. Resume may reuse existing received responses but
must never resend an ambiguous request or regenerate a completed artifact.

Validate the JSON schema. Separately locate source quotations, check unit IDs,
code/theme links and source-note coverage. Exact offsets are computed by code
against original Unicode text, zero-based with an exclusive end, not guessed
by the model. Multiple matches remain ambiguous. Retain invalid semantic links
and missing support as visible integrity flags in intelligible artifacts.
Mechanical checks do not establish correct coding or thematic interpretation.

Outputs: frozen inputs and configuration, prompt/schema, call journals,
`ta_artifacts/<id>/artifact.locked.json`, readable `codes_and_themes.md` reports,
`generation_summary.csv`, `summary.md`, status and final hash manifest.
No accuracy, precision, recall, Credibility or Conformability score is claimed.
No old run, automatic/manual Playbook, Table 3 or manuscript is changed.

## Commands

The executable is
`experiments/warrantroute_claim_detection/run_ta_generation_smoke.py`.
Its `--help` documents `prepare`, `run`, `status` and `pause`.
Use `/opt/anaconda3/bin/python3 -B`. Preparation requires a fresh absolute
`--run-dir` under project Storage and the existing `--source-run`. Running
requires `--authorize-local-inference`; status is read-only. Pause finishes the
current packet. A pause marker must not be cleared without an explicit resume
decision, and the elapsed budget is not reset. A completed run cannot rerun.

The focused source-free unit tests are `test_ta_generation.py`. They cover exact
and ambiguous anchors, malformed output, faulty links retained as review
targets, source-only prompts, context admission, paid-API refusal, missing
response fail-closed behavior and received-response reuse. The first of the
three authorized real-packet calls is also the live grammar-backend smoke;
it remains part of this run even if unsuccessful.
