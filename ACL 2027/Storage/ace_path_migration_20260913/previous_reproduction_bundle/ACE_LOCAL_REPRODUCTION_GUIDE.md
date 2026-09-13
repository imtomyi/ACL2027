# ACE Local Reproduction Guide

Reference environment: Tom's local experiment workspace, captured on 13 September 2026.

This guide defines how to match the recorded local ACE implementation and how to extend it to the four ACE rows in the comparison table. Read the implementation status before running anything. Matching the protocol is achievable. Identical generated text, scores, and execution times across different hardware are not guaranteed, even with temperature zero and a fixed seed.

## 1. Implementation status and scope

| Component | Verified status at capture | Meaning for reproduction |
| --- | --- | --- |
| Dreaddit comparison | Existing queue contains Base, ICL, MIPROv2, GEPA, and two DC conditions | It does not implement the four ACE rows |
| GoEmotions comparison | Existing queue contains Base, ICL, MIPROv2, and GEPA | It does not implement the four ACE rows |
| CaChe / ParlaMint-GB paired pilot | Local ACE offline/online and with/without reference implementations exist | This is the currently implemented local ACE variant |
| Paired reference labels | The 600-annotation manifest is not yet sealed | A complete identical reference-label replay is not available yet |
| Four-corpus ACE benchmark | Not implemented or completed as a unified experiment | The extension below is a specification, not an already tested launch command |

The earlier conversational recommendation of three reflection rounds and online windows of 15 described an upstream-style configuration. **Those values do not describe Tom's implemented local ACE pilot.** To reproduce the existing local pilot, use one generation, one reflection, one curation, and an online window of one. Do not combine settings from the two variants.

No experiment was started, interrupted, or reprioritized to create this guide. Do not execute a second inference queue on Tom's machine while the existing GoEmotions queue is running.

## 2. Authoritative artifacts

This directory contains:

- `reference_manifest.json`: observed environment, package versions, upstream commit, model digest, tokenizer revision, and file hashes.
- `requirements.reference.txt`: all 88 Python distributions observed in the current reference virtual environment. This is a version snapshot, not a wheel lock with distribution hashes.
- `model_runtime.json`: observed Ollama model parameters and chat template.
- `snapshot/`: copies of 30 relevant local source, prompt, configuration, and split-manifest files, preserving repository-relative paths.
- `verify_reference.py`: a read-only checker for source/data hashes, packages, tokenizer files, and the local model server. It makes no inference requests.

Raw corpus excerpts, model weights, the tokenizer cache, and prediction or annotation payloads are not included. Obtain the required data through the project's authorized distribution, preserving its bytes. A Git clone by itself may omit local datasets and vendored files. Use `required_data_sha256` and `source_and_config_sha256` as the transfer inventory.

The snapshot contains original absolute paths in historical frozen configurations. Preserve those files as provenance. Do not silently edit their hashes to make a relocated run pass.

## 3. Match the reference environment

| Component | Observed value |
| --- | --- |
| Hardware | Apple M4 Pro, Mac16,8 |
| Unified memory | 25,769,803,776 bytes (24 GiB) |
| OS | macOS 26.6.2, build 25G83, arm64 |
| Python | 3.13.2 |
| Ollama | 0.33.3 |
| Model | `qwen3:8b`, 8.2B, GGUF Q4_K_M |
| Model manifest digest | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Transformers | 5.16.1 |
| Tokenizers | 0.23.2 |
| DSPy / GEPA | 3.0.3 / 0.0.7 |
| OpenAI Python client | 2.54.0 |
| Optuna / NumPy / HTTPX | 5.0.0 / 2.5.3 / 0.28.1 |
| Tokenizer repository | `Qwen/Qwen3-8B` |
| Tokenizer revision | `b968826d9c46dd6066d109eabc6255188de91218` |

These are observed values at capture, not a claim that the entire historical run recorded every runtime setting. Server parallelism, GPU kernels, thread counts, and all service environment variables were not frozen by the existing experiment. Record these on the destination too. Do not claim bitwise equivalence solely because this table matches. A Linux/CUDA or MLX execution is a different inference backend and should be reported as such.

On the destination, create a new virtual environment using Python 3.13.2 and install the version snapshot:

```sh
python3.13 -m venv .venv-ace-reference
.venv-ace-reference/bin/python -m pip install -r "/path/to/ace_reproduction_20260913/requirements.reference.txt"
```

Check the actual Python patch version. If a pinned package cannot be installed on that platform, record the incompatibility instead of substituting another version and calling it identical. For stricter archival reproducibility, also retain platform-specific wheels and SHA-256 hashes.

Install the same Ollama version through its official release mechanism. Obtain the exact model artifact from the reference installation or an archive. `ollama pull qwen3:8b` alone is not sufficient because a tag can change. Verify the returned model digest using `/api/tags`. Preserve the model manifest, every referenced blob, and the chat template rather than reconstructing a new model under the same name.

Populate the Hugging Face cache with the pinned tokenizer revision, including all files listed in the manifest. The current `Native` adapter loads it with `local_files_only=True` and an unpinned repository name, so the destination's cache resolution must select this exact revision. Verify file hashes, not just the directory name.

## 4. Preserve inference behavior

All local ACE roles use the same Qwen model through the native Ollama endpoint:

```text
POST http://127.0.0.1:11434/api/chat
model: qwen3:8b
stream: false
think: false
keep_alive: 30m
options.num_ctx: 32768
options.temperature: 0
options.seed: 42
options.num_predict: role-specific cap
HTTP timeout: 1800 seconds
```

The model's observed defaults include `top_k=20`, `top_p=0.95`, and `repeat_penalty=1`. Its default temperature is 0.6, but each local ACE request overrides it to zero. Preserve the full model template and stop settings in `model_runtime.json`. Do not switch to an OpenAI-compatible endpoint, change the message roles, reserialize prompt data differently, or replace JSON schema mode with free text without recording a new implementation variant.

The shared adapter counts the rendered chat template using:

```python
tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    enable_thinking=False,
    return_dict=False,
)
```

`return_dict=False` is essential with the captured Transformers version. Counting the fields of a returned mapping instead of token IDs caused an earlier preparation bug. Reject requests whose counted input plus reserved output exceeds 32,768 tokens. Preserve the current truncation checks and role-specific failure behavior from the snapshot. The current shared adapter does not treat every role's output-length termination identically; do not describe it as a universal truncation rejection policy.

Run a single experiment queue and serial requests. Equal settings do not imply equal throughput on a different machine.

## 5. Identify the ACE variant

Official source: [ace-agent/ace](https://github.com/ace-agent/ace), pinned to commit `82709de050e1db6e6ef2f07bcb0393560b94992a`.

| Property | Upstream README/example | Implemented local paired pilot |
| --- | --- | --- |
| Orchestration | Official ACE orchestrator | Custom durable serial loop |
| Reflection | Up to three rounds on incorrect answers | One reflection per adaptation sample |
| Regeneration after reflection | Supported in training | No reflection/regeneration loop |
| Online evaluation window | Example uses 15 samples | One sample |
| Curator | Official implementation | Official templates and merging utilities, accepting ADD operations only |
| Bullet analyzer | Optional, disabled by default | Disabled |
| Offline checkpoint choice | Validation-based best playbook | Last playbook after one epoch |
| Playbook token budget | Example uses 80,000 | 8,000 |
| Role output caps | Example uses 4,096 | Generator 1,024; reflector 1,536; curator 2,048 |

Use the label **“ACE-derived local serial variant”** for the current pilot, with these differences disclosed. Do not describe it as exact reproduction of the paper's financial experiments or of the upstream orchestrator. Source: [pinned README](https://github.com/ace-agent/ace/blob/82709de050e1db6e6ef2f07bcb0393560b94992a/README.md).

The local loop preserves sectioned bullets, IDs, and helpful/harmful counters. For an invalid reflection it retains the incoming memory and next ID. For invalid or oversized curator operations it retains the playbook after valid counter updates, rather than accepting the candidate additions. This distinction matters for checkpoint equality. Preserve the exact implementation, including empty section names, parsing, JSON serialization, and failure handling.

## 6. Define GT access explicitly

The upstream `no_ground_truth=True` option hides the answer string from reflection, but the orchestrator still computes correctness from the target, supplies match/mismatch feedback, and uses correctness to control reflection and stopping. Thus this option is not strict absence of target-derived feedback. In a binary task, correctness plus the predicted label can reveal the target. Inspect [the pinned training loop](https://github.com/ace-agent/ace/blob/82709de050e1db6e6ef2f07bcb0393560b94992a/ace/ace.py#L475-L563).

For the strict local protocol:

- **GT yes:** a human benchmark label may reach adaptation only after the current evaluation prediction is saved. Never include it in that prediction's prompt.
- **GT no:** target values, correctness flags, target-based stopping, and target-based playbook selection must not influence adaptation. The isolated scorer may read targets to calculate the reported metric.
- **Reference yes (dagger):** CaChe and ParlaMint use frozen, unverified model annotations, not human GT. Display `GT yes†` and explain the dagger.
- Judge decisions never become adaptation feedback in any condition.

The current paired pilot uses reference feedback rather than benchmark correctness and does not inherit the upstream correctness-controlled retry loop. Strict GT no is not achieved by merely changing the upstream flag.

## 7. Freeze data and ordering

Never download a convenient alternate release or reconstruct splits from counts alone. Transfer the exact inputs and ordered IDs listed in `reference_manifest.json`.

| Dataset | Adaptation / train | Validation | Evaluation | Task |
| --- | ---:| ---:| ---:| --- |
| Dreaddit | 2,249 | 555 | 712 | Binary stress classification, 0=no stress, 1=stress |
| GoEmotions | 43,410 | 5,426 | 5,427 | Exact set of labels from the 28-label release |
| CaChe pilot | 100 | None | 200 | Provisional topic coding |
| ParlaMint-GB pilot | 100 | None | 200 | Provisional topic coding |

Dreaddit uses the project's deidentified `records.jsonl` and the ordered IDs in `comparison_preparation_20260912/splits.json`. Source SHA-256: `86ba43a89d9ef52f5377d35c12d26690b820f24ce11bc6540eeae57605654d3a`. The split-manifest SHA-256 is `152f22a3abb3589010e7c34a60cb96efedf7b60ae90c4a1cd212239018a44ba1`.

GoEmotions TSV hashes are:

```text
train  1c254a142be5c00e80d819b9ae1bbd36d94b2eeb8f4b1271846508d57e57d9c5
dev    575489c079c9de1097062a01738f998590d6b7ead66dd1c9fd1d2ba01fd8bc62
test   0587b2dd8b27b97352adbfc3fb083d46005c8946657fdc2b1ca8b1cc7f1f8be4
```

Keep the `emotions.txt` order. Label 27 is neutral. Do not replace multi-label targets with one label or filter the evaluation set to single-label examples.

The CaChe and ParlaMint selections are pilots, not complete-corpus evaluations. Their adaptation and test sessions are disjoint, but speakers may recur across ParlaMint sessions. Preserve the four selected JSONL files and their manifest. Keep the provisional codebooks exactly as captured in the paired frozen configuration. They are not an official CAP taxonomy.

## 8. Four ACE rows for Dreaddit and GoEmotions

This section specifies an extension of the implemented local variant. **The benchmark ACE adapters and launch entry point still need implementation and verification.** Do not run the existing GoEmotions script expecting it to produce ACE rows.

Use one epoch, the local role caps from Section 5, and the recorded order. Initialize a separate empty playbook and `next_id=1` for every dataset-condition pair. Do not share response caches between conditions unless the full request identity is verified. No condition starts from another condition's learned playbook.

| Condition | Adaptation sequence | Final evaluation |
| --- | --- | --- |
| Offline GT yes | For each training item: generate, expose label, reflect once, curate once | Freeze the last playbook; generate once per test item |
| Offline GT no | Same training inputs; generate, reflect once without target feedback, curate once | Freeze the last playbook; generate once per test item |
| Online GT yes | For each test item: generate and persist the scored prediction, then expose label, reflect once, curate once | Aggregate only persisted pre-update predictions |
| Online GT no | For each test item: generate and persist, reflect without target feedback, curate once | Aggregate only persisted pre-update predictions |

Both offline conditions use the last checkpoint so strict GT no does not acquire labels through validation selection. Validation can be reported separately after protocol freezing, but cannot choose this variant's final playbook. This differs from the upstream validation-selected variant.

Implement a dataset adapter following the [official extension guide](https://github.com/ace-agent/ace/blob/82709de050e1db6e6ef2f07bcb0393560b94992a/EXTENDING_ACE.md): standardized context/question/target fields, task-specific parsing and correctness, and aggregate scoring. Keep the evaluation target separate from model inputs. The upstream extractor expects `final_answer`; the existing GoEmotions direct runner uses `label_ids`. An explicit, tested mapping is required. Renaming a dataset in the finance command does not provide this mapping.

The extension must freeze complete task prompts, role templates, output schemas, serialized label feedback, and parsers before its first inference call. This guide does not supply those unimplemented adapter bytes and cannot stand in for their hash manifest. The benchmark ACE generation cap proposed here is 1,024, while existing GoEmotions Base/ICL direct generation uses 512. Disclose that difference or define a separate budget-matched experiment before execution. Never retroactively change the completed baseline protocol.

## 9. Reproduce the existing paired pilot on another machine

Use a separate destination checkout or work directory. Preserve this layout:

```text
replica-root/
  ACL 2027/
    experiments/paired_feedback/run.py
    experiments/gt_free_corpora/run.py
    experiments/dreaddit_icl/...
    Storage/paired_feedback/run_20260912/data/...
    Storage/dreaddit_icl/dynamic-cheatsheet/...
  ace_paper/original_sources/ace/...
```

Restore the source files from `snapshot/` into matching relative locations, including vendored prompt and DC dependency files. Transfer the required data separately. The full inventory is in the manifest. The source resolves project roots relative to its own location, so the destination does not need Tom's username or home directory.

First run the Section 11 checker on the restored files, including historical configurations. Then, for a **fresh** paired run, move the historical paired frozen configuration outside that destination run directory as provenance, leaving the selected `data/` files as the run inputs. Let the unchanged runner write its new configuration with the destination's absolute paths. Compare its scientific fields and each source hash to the captured manifest; only path relocation may differ. Do not overwrite an existing run to accomplish this. The strict byte checker will flag the relocated configuration after launch; this is expected and must be explained by the recorded path-only comparison, not by changing the reference hashes.

The paired runner's real launch command, executed only on the prepared destination, is:

```sh
.venv-ace-reference/bin/python "ACL 2027/experiments/paired_feedback/run.py"
```

This launches the **entire existing seven-method, two-corpus pilot**, including reference preparation and DC, not just ACE. It has no documented ACE-only CLI filter. An ACE-only launcher would be a separately reviewed change. Do not invent command-line switches for the current script.

The runner generates and seals all 600 reference annotations before comparisons. The reference manifest was not sealed on Tom's machine at capture. Therefore, a destination that generates them independently is a new run under the same protocol, not an exact replay of an existing fixed annotation set. For fixed-reference replication, wait for and transfer the completed sealed set, preserving annotation and source hashes. Do not fill the missing annotations with placeholders.

For **checkpoint continuation**, transfer a consistent stopped checkpoint, predictions, role caches, playbook, next bullet ID, annotations, and source snapshot. Do not copy a live adapting directory piecemeal and call it consistent. The historical paired configuration contains absolute path keys and fails direct equality after relocation. A documented path-only migration with semantic/hash verification is required before resuming that checkpoint. This guide does not apply that migration or claim it has been tested.

## 10. Score the same predictions

Accuracy uses all designated test examples, including invalid outputs in the denominator. Dreaddit uses label equality. GoEmotions uses equality of the entire normalized label set. Report Micro-F1 and Macro-F1 separately. Invalid GoEmotions predictions are incorrect for accuracy and empty sets for F1. Use the captured parser rather than silently repairing invalid answers.

For CaChe and ParlaMint, report **Reference agreement**, the exact topic-set match against the sealed model annotations. Human-GT accuracy and F1 are N/A. These model-supervised exploratory results remain in Storage and are not evidence for manuscript result placeholders under current project policy.

Conformability is a separate local, same-family LLM assessment of source-grounded reasoning, not human validation or benchmark correctness. Reuse the exact rubric and schema in the snapshot. Its four criteria are `traceable_basis`, `faithful_meaning`, `supported_scope`, and `no_invented_facts`. Any false criterion yields failure; otherwise any null yields unresolved; otherwise the answer passes. The prompt requests a reason of at most 45 words, while the current validator accepts at most 60; preserve that behavior when replaying the current implementation.

The judge receives only the source and anonymized evaluated answer, plus the fixed task/codebook context. Hide benchmark/reference labels, method identity, demonstrations, and memory. Use the same model, temperature zero, seed 42, thinking off, and a 384-token output cap. Up to three technical attempts are allowed by the current judgment loop. Never retry a valid false or null to improve the score. A final percentage requires the full denominator and zero unresolved cases. Save failed attempts and unresolved counts.

Offline scores come from the frozen-playbook test run. Online scores and Conformability use the prediction saved before feedback. Never substitute an answer regenerated after seeing the label.

## 11. Verification and acceptance

Run the checker against the destination before starting inference:

```sh
.venv-ace-reference/bin/python "/path/to/ace_reproduction_20260913/verify_reference.py" \
  --repo-root "/path/to/replica-root" \
  --tokenizer-dir "/path/to/pinned/tokenizer/snapshot"
```

The checker reports missing/mismatched inputs and package versions without printing corpus text. Optional `--check-server` reads Ollama version, model digest, parameters, and template without loading or generating with the model. Hardware/platform differences are reported as notes; file, package, Python, and requested server-check failures produce a nonzero exit status. Run it on the staged historical snapshot before relocating the paired configuration for a fresh run. It does not certify scientific equivalence by itself.

Before launching new benchmark ACE rows, also verify these behavioral requirements with isolated software tests:

1. GT-no adaptation requests and control flow remain unchanged if hidden target labels are permuted, using fixed mocked model responses for the software test only.
2. Online predictions are durably saved before feedback affects the next memory state.
3. Offline test generation cannot mutate the playbook or read targets.
4. Checkpoint continuation preserves completed item IDs/order, playbook bytes, next ID, and pending phase without double-applying updates.
5. Invalid reflection/curator outputs and overflow follow the frozen failure policy.
6. Parsers and metric aggregation handle multi-label sets, invalid outputs, and unresolved judgments correctly.

Software fixtures are not experimental observations and must never enter results. Verify deterministic scoring on transferred saved predictions separately from fresh model generation. Recomputed metrics should match for identical saved artifacts; a fresh GPU generation may diverge and then cause a different adaptive trajectory.

Archive the final config, complete ordered predictions, adaptation history, final playbook, role-call metadata, elapsed times, metrics, and failure counts. Do not call a run complete because all generation calls returned if output or judgment records remain unresolved.

## 12. Runtime planning

For the implemented one-round variant, let `A` be adaptation items, `T` test items, and `g`, `r`, `c`, and `j` be measured average generation, reflection, curation, and judgment times:

```text
Offline row: A × (g + r + c) + T × g + T × j
Online row:  T × (g + r + c) + T × j
```

These are planning approximations, excluding reference preparation, retries, cache effects, and growing prompt costs. GT conditions may have different actual role times. Measure the real ACE roles on the destination; do not use MIPROv2's short classification-call latency as an ACE estimate. The upstream regeneration/windowed variant has a different call schedule.

The strongest claim supported by this package is a verifiable snapshot of the current local environment and implemented pilot plus a specified benchmark extension. A claim of exact four-row benchmark reproduction requires the missing adapters, their tests, a frozen executable configuration, and completed outputs.
