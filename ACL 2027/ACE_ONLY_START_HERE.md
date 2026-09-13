# ACE-only replication: start here

Open [the English execution prompt](experiments/ace_only/PROMPT.md), copy its entire
contents into an agent with local filesystem and terminal access, and give it
this GitHub checkout. The prompt instructs the agent to implement and test a
dedicated ACE-only runner, then execute it. The package currently provides the
preparation tools and scientific specification, not a completed execution runner.

Repository: https://github.com/imtomyi/ACL2027/tree/seunghyun

The inner project folder is **`ACL 2027`**, including the space. All experiment
paths are relative to this folder. You do not need the external sibling
`ace_paper` folder or an account named `tom`.

```sh
GIT_LFS_SKIP_SMUDGE=1 git clone --single-branch --branch seunghyun \
  https://github.com/imtomyi/ACL2027.git ACL2027-ace-only
cd "ACL2027-ace-only/ACL 2027"
```

The new package is newer than commit `396d3037c`. Use the branch version containing
this marker and record its actual commit. A default-branch checkout may not
contain it. Skipping LFS logs does not skip any required ACE-only package input.

## Fixed scope

Only ACE Offline GT yes/no and ACE Online GT yes/no. No Base, ICL, MIPROv2, GEPA,
DC, or GPT-5 calls. Four datasets × four ACE conditions = 16 target cells.

| Dataset | Adaptation per offline condition | Evaluation per condition | Shared limit for all four conditions | Rough time to finish all four without the limit |
| --- | ---: | ---: | ---: | --- |
| Dreaddit | 20 | 100 | 2 hours | 2.5–6 hours |
| GoEmotions | 20 | 100 | 2 hours | 2.5–6 hours |
| CaChe | 20 | 100 | 2 hours | 3–8 hours |
| ParlaMint-GB | 20 | 100 | 2 hours | 3–8 hours |

One pass, one reflection and one curation per adaptation item, independent empty
initial playbooks, and the same fixed test IDs/order across conditions. Online
conditions do not use the 20 offline adaptation items. Qwen3-8B Q4_K_M, thinking
off, temperature 0, seed 42, and serial execution.

Execution stops after at most roughly eight hours across the four datasets,
plus bounded shutdown overhead. Software preparation is additional. The limit
does **not** guarantee complete cells. Preserve incomplete counts and statuses.
The unconstrained estimates are provisional: early role timing used only four
generation/reflection calls and three curator calls. See
[timing assumptions](experiments/ace_only/timing_plan.json).

Report Acc and Conformability for Dreaddit/GoEmotions. CaChe/ParlaMint GT yes† uses
unverified model annotations: human Acc is N/A, with Reference agreement reported
separately. All results are local diagnostic task transfers, not exact
reproduction of the ACE finance paper.

## Exact locations

| Resource | Project-relative location |
| --- | --- |
| Copy/paste execution prompt | [experiments/ace_only/PROMPT.md](experiments/ace_only/PROMPT.md) |
| Frozen tasks, codebooks and budgets | [experiments/ace_only/protocol.json](experiments/ace_only/protocol.json) |
| Fixed 20/100 IDs and text hashes | [experiments/ace_only/selection.json](experiments/ace_only/selection.json) |
| Required inputs and download/hash inventory | [experiments/ace_only/data_sources.json](experiments/ace_only/data_sources.json) |
| Public-data reconstruction and preflight | [experiments/ace_only/prepare.py](experiments/ace_only/prepare.py) |
| Native inference adapter | [experiments/ace_only/native.py](experiments/ace_only/native.py) |
| Conformability rubric | [experiments/ace_only/rubric.py](experiments/ace_only/rubric.py) |
| Package integrity inventory | [experiments/ace_only/package_manifest.json](experiments/ace_only/package_manifest.json) |
| Python environment versions | [Storage/ace_reproduction_20260913/requirements.reference.txt](Storage/ace_reproduction_20260913/requirements.reference.txt) |
| Official ACE code, prompts, license and paper | [ace_paper/README.md](ace_paper/README.md) |
| New experiment outputs | `Storage/ace_only/<run_id>/` (created by the execution agent) |

## Data preparation

From the inner project directory, using Python 3.13.2:

```sh
python3.13 -m venv .venv-ace-only
.venv-ace-only/bin/python -m pip install -r \
  Storage/ace_reproduction_20260913/requirements.reference.txt
.venv-ace-only/bin/python experiments/ace_only/prepare.py --download-missing
```

This is a preparation command, not an experiment launch. It reconstructs ignored
public inputs and checks all four fixed selections. It does not call the model.
Do not commit the virtual environment or downloaded corpus text.

- Dreaddit: obtain the original archive from the author's recorded URL, check
  archive/CSV hashes, and reproduce `dataset/deidentified/dreaddit/records.jsonl`
  with the captured processor. Identical reconstruction was verified.
- GoEmotions: download the recorded files from Google Research commit
  `2adf640a14f11025ae5a9d0ec493b78530d276d3`; each hash matches the reference.
- CaChe/ParlaMint: use the already preserved repository pool files under
  `Storage/paired_feedback/run_20260912/data/`; no outside project copy is needed.

All paths, sizes, source hashes, and public download locations are recorded in
`data_sources.json`. Model weights and the tokenizer cache are not stored in Git;
the prompt specifies their identities and setup checks. Source material does not
grant authorization to modify the experiment.

The isolated portability check rebuilt missing public files in a different
project path and verified 20 adaptation plus 100 evaluation IDs for every corpus,
with zero inference calls. This validates preparation, not an unimplemented
runner or completed experimental scores. See
[validation record](experiments/ace_only/VALIDATION.md).
