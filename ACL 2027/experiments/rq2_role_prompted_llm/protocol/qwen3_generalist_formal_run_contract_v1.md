# Qwen3 Generalist formal run contract v1

## Boundary

This runner applies the frozen Qwen3 8B Generalist reviewer to the authorized
Dreaddit test packet bank. It cannot authorize corpus use or manufacture a
manuscript value. Its only persistent outputs are a source-free observation
bundle and observation seal plus a restricted source-bearing raw-execution
bundle and its content-free seal. All four outputs remain in one private
`Storage/` directory.

## Fail-closed order

Before checking the existence, permissions, or contents of the packet bank,
and before contacting Ollama, the runner validates four source-free records:

1. the scoring study freeze accepted by the scoring exporter;
2. its exact formal readiness report with all ten Dreaddit gates complete;
3. the exact packet-bank seal produced by the packet sealer; and
4. an execution freeze binding the study freeze, readiness report, every
   packet-seal binding, packet-bank hash and denominator, this runner, this
   contract, and an approved retention and deletion scope for raw records.

The execution freeze has document type
`warrantroute_qwen3_generalist_execution_freeze_v1`, status
`bound_to_authorized_study_freeze`, and the exact fields enforced in the
runner. It is a text-free record stored mode 0600 under a mode-0700
`governance/local/` directory. It does not replace or expand the approval in
the study freeze. Its raw-record scope must bind the same approval record as
the study freeze, identify the completed `retention_deletion_controls` gate,
authorize source-bearing raw records in restricted mode-0600 storage, name an
authorized accessor group and retention deadline, and require a deletion
record. Execution after that deadline is blocked.

The packet-bank seal must bind the same readiness report, Qwen component,
candidate generator, item count, item-ID set, scoring contract, and packet-bank
hash as the study and execution freezes. Passing these checks is required but
does not create authorization outside the bound study.

## Source-bearing execution

Only after metadata passes does the runner open the mode-0600 packet bank below
a mode-0700 `Storage/` directory. It verifies the sealed file hash, wrapper,
test split, in-domain role, privacy-clearance declaration, exact item count,
opaque item-ID set, and evaluator-item schema. Hidden truth, route, generator,
or flaw fields are forbidden in every displayed item.

The runner then checks the frozen local Ollama version, Qwen model name, and
model digest. Requests use the source-free component's hardened system prompt,
rating guide, schema transport, fixed seeds, disabled tools, disabled thinking,
and disabled truncation and context shifting. Every item receives three
stateless requests with seeds `2027082601`, `2027082602`, and `2027082603`.
Each complete request is constructed once before model contact and those exact
UTF-8 bytes are both sent and retained. The network helper accepts only a
hash-authorized prebuilt request for a validated item and repetition.
Repetition 1 is primary. Repetitions 2 and 3 are retained for stability
analysis. Each item-repetition pair receives one attempt, with no retry or
replacement. A malformed, failed, timed-out, truncated, or context-invalid
response remains terminal. The service identity must be unchanged after the
last item.

## Outputs

The restricted raw-execution bundle stores the exact base64-encoded request and
response bodies, terminal status, seed, and parsed rating for all three
repetitions. It is marked source-bearing and written mode 0600 below
`Storage/`. A separate content-free seal binds it to the exact study freeze,
execution freeze, packet-bank seal, runner, runner contract, and approved raw
retention and deletion scope.

The observation bundle has exactly the shape consumed by
`export_qwen3_generalist_score.py` and contains repetition 1 only. A valid
rating retains the model's scored fields but replaces its free-text rationale
with a fixed source-free sentence. Its private-execution hash equals the
canonical SHA-256 of the corresponding repetition-1 raw record. Repetitions 2
and 3 never enter the aggregate scorer.

The raw bundle, raw seal, source-free observation bundle, and observation seal
are created mode 0600 in the same mode-0700 `Storage/` directory, without an
overwrite option. None is itself a manuscript score. The separate scoring
exporter must still validate the private truth map and compute the aggregate
result. The observation seal uses document type
`warrantroute_qwen3_generalist_observation_seal_v2`. In addition to its bundle
hash and completion fields, it binds the execution freeze, packet-bank seal,
raw bundle, raw seal, runner, runner contract, and canonical map and set
commitments for every repetition-1 raw-record hash. The current scoring
exporter validates this v2 seal and its full execution, packet, raw-bundle,
raw-seal, runner, contract, and repetition-1 record-hash chain before scoring.

The v2 observation seal has exactly these fields: `document_type`,
`seal_version`, `seal_id`, `status`, `sealed_at_utc`,
`study_freeze_sha256`, `execution_freeze_sha256`,
`packet_bank_seal_sha256`, `raw_execution_bundle_sha256`,
`raw_execution_seal_sha256`, `runner_sha256`, `runner_contract_sha256`,
`primary_raw_record_hash_map_sha256`,
`primary_raw_record_hash_set_sha256`, `observation_bundle_sha256`,
`record_count`, `all_frozen_items_terminal`, and `source_text_included`.

## Commands

The current source-free state check reads no packet, contacts no model, and
writes nothing:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_formal.py dry-run
```

The formal interface is:

```sh
python3 experiments/rq2_role_prompted_llm/scripts/run_qwen3_generalist_formal.py run \
  --execution-freeze /ABS/PATH/governance/local/execution_freeze.local.json \
  --study-freeze /ABS/PATH/governance/local/scoring_study_freeze.local.json \
  --readiness-report /ABS/PATH/governance/local/readiness_report.local.json \
  --packet-bank-seal /ABS/PATH/Storage/PRIVATE_RUN/packet_bank_seal.json \
  --packet-bank /ABS/PATH/Storage/PRIVATE_RUN/evaluator_items.private.json \
  --raw-execution-bundle /ABS/PATH/Storage/PRIVATE_RUN/raw_executions.private.json \
  --raw-execution-seal /ABS/PATH/Storage/PRIVATE_RUN/raw_execution_seal.json \
  --observation-bundle /ABS/PATH/Storage/PRIVATE_RUN/observations.private.json \
  --observation-seal /ABS/PATH/Storage/PRIVATE_RUN/observation_seal.json \
  --sealed-at-utc YYYY-MM-DDTHH:MM:SSZ
```
