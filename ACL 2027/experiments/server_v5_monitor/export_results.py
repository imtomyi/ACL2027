#!/usr/bin/env python3
"""Render current v5 metadata into a reproducible Markdown results snapshot."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import statistics

CORPORA = [('dreaddit', 'Dreaddit'), ('goemotions', 'GoEmotions'),
           ('cache', 'CaChe'), ('parlamint_gb', 'ParlaMint-GB')]
METHODS = {'base': 'Base', 'icl': 'ICL', 'miprov2': 'MIPROv2', 'gepa': 'GEPA', 'ace': 'ACE', 'dc_cu': 'DC (CU)'}
STATUSES = {'prediction_complete': 'Predictions complete',
            'prediction_complete_with_failures': 'Finished with invalid outputs',
            'withheld_failed_development_probe': 'Held: development failure',
            'queued': 'Queued', 'running': 'Running', 'failed': 'Failed',
            'paused': 'Paused', 'unstarted': 'Not started'}


def load(path):
    return json.loads(path.read_text())


def key(cell):
    return tuple(cell[k] for k in ['dataset', 'phase', 'method', 'adaptation_gt'])


def iso(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def filelink(label, path):
    return '[{}](<{}>)'.format(label, path.resolve())


def gt(value):
    return {'yes': '✓', 'no': '✗', 'not_applicable': '—'}[value]


def phase(value):
    return {'baseline': 'Base', 'offline': 'Offline', 'online': 'Online'}[value]


def status(row):
    raw = row['state'].get('status', 'unstarted')
    return STATUSES.get(raw, raw)


def prediction_done(row):
    return row['state'].get('predicted') == 100 and row['state'].get('attempted') == 100


def fully_done(row):
    state, cell, metrics = row['state'], row['cell'], row['metrics']
    return (prediction_done(row) and state.get('judged') == 100 and metrics.get('conformability') is not None
            and (cell['method'] not in ['ace', 'dc_cu'] or state.get('updated') == 100))


def final_value(row, metric):
    state, metrics = row['state'], row['metrics']
    if state.get('attempted') != 100:
        return None
    if metric == 'conformability' and state.get('judged') != 100:
        return None
    return metrics.get(metric)


def aggregate(rows, metric):
    values = [final_value(r, metric) for r in rows]
    ready = [v for v in values if v is not None]
    if len(ready) != len(rows):
        return '—' if not ready else '— ({}/{})'.format(len(ready), len(rows))
    return '{:.2f} ± {:.2f}'.format(statistics.mean(ready), statistics.stdev(ready))


def counts(rows, field):
    return sum(r['state'].get(field, 0) for r in rows)


def memory_updates(rows):
    # Only ACE/DC commit memory updates. Optimizer stages reuse `updated` for development evaluations.
    return counts([r for r in rows if r['cell']['method'] in ['ace', 'dc_cu']], 'updated')


def collect(prep, protocol):
    paths = [(prep/'live', 'prediction_manifest.json')]
    paths += [(p.parent, 'manifest.json') for p in sorted(prep.glob('*/manifest.json'))]
    sources, selected, notices = [], {}, []
    backbone = None
    entries = []
    for directory, manifest_name in paths:
        report_path, manifest_path = directory/'results.json', directory/manifest_name
        if not report_path.exists() or not manifest_path.exists():
            continue
        manifest, report = load(manifest_path), load(report_path)
        runtime = manifest['runtime']
        model_identity = (runtime['model'], runtime['model_digest'], runtime['quantization'])
        if backbone is None:
            backbone = model_identity
        if model_identity != backbone:
            notices.append('Excluded a different backbone/revision at '+directory.name)
            continue
        entries.append((manifest.get('sealed_at', 0), directory, manifest, report))
    if not entries:
        raise RuntimeError('No measured v5 report is available; refusing to create an empty result claim')
    for _, directory, manifest, report in sorted(entries, key=lambda x: x[0]):
        by_id = {r['cell']['id']: r for r in report['rows']}
        admitted = {c['id'] for c in manifest.get('admitted_cells', manifest['cells'])}
        held = set(manifest.get('withheld_cells', []))
        for cell in manifest['cells']:
            row = by_id.get(cell['id'], dict(cell=cell, state={'status': 'queued'}, metrics={}))
            row = dict(row, stage=directory.name, protocol=manifest['protocol'], seal=manifest['seal_sha256'],
                       admitted=cell['id'] in admitted)
            if cell['id'] in held:
                row['state'] = dict(row['state'], status='withheld_failed_development_probe')
            identity = key(cell)+(cell['seed'],)
            if row['admitted'] or identity not in selected:
                selected[identity] = row
        sources.append(dict(path=str(directory/'results.json'), report_updated_at=report['updated_at'],
            report_sha256=hashlib.sha256((directory/'results.json').read_bytes()).hexdigest(),
            seal_sha256=manifest['seal_sha256'], protocol=manifest['protocol']))
    panel = []
    expected = set()
    for condition in protocol['conditions']:
        for seed in protocol['seeds']:
            identity = key(condition)+(seed,)
            expected.add(identity)
            row = selected.get(identity)
            if row is None:
                row = dict(cell=dict(condition, seed=seed), state={'status': 'unstarted'}, metrics={},
                           stage=None, admitted=False)
            panel.append(row)
    if set(selected)-expected:
        raise RuntimeError('Report includes a condition outside the fixed v5 panel')
    assert len(panel) == len(expected) == 84
    judges = []
    for path in sorted(prep.glob('evaluation/*/results.json')):
        if (path.parent/'manifest.json').exists():
            manifest = load(path.parent/'manifest.json')
            judges.append((manifest.get('sealed_at', 0), path.parent, manifest, load(path)))
    judge_sources = []
    for _, directory, manifest, report in sorted(judges, key=lambda x: x[0]):
        by_identity = {key(r['cell'])+(r['cell']['seed'],): r for r in report['rows']}
        for index, row in enumerate(panel):
            judged = by_identity.get(key(row['cell'])+(row['cell']['seed'],))
            # A judgment applies only to the exact prediction cohort it read.
            if judged is None or judged['prediction_seal_sha256'] != row.get('seal'):
                continue
            s = judged['state']
            panel[index] = dict(row, judge=manifest['protocol'],
                state=dict(row['state'], judged=s.get('processed', 0), judge_resolved=s.get('resolved', 0)),
                metrics=dict(row['metrics'], conformability=s.get('conformability')))
        judge_sources.append(dict(path=str(directory/'results.json'), report_updated_at=report['updated_at'],
            report_sha256=hashlib.sha256((directory/'results.json').read_bytes()).hexdigest(),
            seal_sha256=manifest['seal_sha256'], protocol=manifest['protocol'],
            same_model_judge=manifest.get('same_model_judge'), provisional=manifest.get('provisional'),
            human_calibration=manifest.get('human_calibration')))
    derived_sources = []
    for path in sorted(prep.glob('derived/*/results.json')):
        report = load(path)
        if report.get('status') != 'validated':
            notices.append('Derived metric report not validated: '+path.parent.name)
            continue
        by_identity = {key(r['cell'])+(r['cell']['seed'],): r for r in report['rows']}
        for index, row in enumerate(panel):
            derived = by_identity.get(key(row['cell'])+(row['cell']['seed'],))
            # Fill only a stage F1 withheld because of invalid outputs, for the exact prediction cohort.
            if (derived is None or derived['prediction_seal_sha256'] != row.get('seal') or not derived['invalid_n']
                    or row['metrics'].get('micro_f1') is not None):
                continue
            panel[index] = dict(row, derived_f1=report['protocol'], invalid_n=derived['invalid_n'],
                metrics=dict(row['metrics'], micro_f1=derived['micro_f1'], macro_f1=derived['macro_f1']))
        derived_sources.append(dict(path=str(path), protocol=report['protocol'], rule=report['rule'],
            report_updated_at=report['updated_at'], validation=report['validation']))
    pointer = lambda name: load(prep/name) if (prep/name).exists() else {}
    return dict(model=backbone, rows=panel, sources=sources, judge_sources=judge_sources,
                derived_sources=derived_sources, notices=notices,
                execution=pointer('ACTIVE_ADAPTATION_STAGE.json'),
                optimization=pointer('ACTIVE_OPTIMIZATION_STAGE.json'))


APPWORLD_SPLITS = {'train': 90, 'test_normal': 168, 'test_challenge': 417}
APPWORLD_ROWS = [('ReAct', '—', 'qwen3_8b_ReAct_{}'), ('ACE offline', '✓', 'qwen3_8b_ACE_offline_with_GT_evaluation_{}'),
                 ('ACE offline', '✗', 'qwen3_8b_ACE_offline_no_GT_evaluation_{}'), ('ACE online', '✗', 'qwen3_8b_ACE_online_no_GT_{}')]
# Zhang et al. (ICLR 2026), Table 1, DeepSeek-V3.1: Test-Normal TGC, SGC, Test-Challenge TGC, SGC.
APPWORLD_PAPER = {('ReAct', '—'): (63.7, 42.9, 41.5, 21.6), ('ACE offline', '✓'): (76.2, 64.3, 57.3, 39.6),
                  ('ACE offline', '✗'): (75.0, 64.3, 54.4, 35.2), ('ACE online', '✗'): (69.6, 53.6, 66.0, 48.9)}


def appworld_lines(prep, storage):
    """Separate AppWorld section: our Qwen3-8B reproduction, the paper's reference values, and progress."""
    mirror = prep/'appworld'
    if not (mirror/'orchestrator/state.json').exists():
        return []
    state, jobs = load(mirror/'orchestrator/state.json'), load(mirror/'jobs.json')
    progress = load(mirror/'progress.json') if (mirror/'progress.json').exists() else {}
    cell = lambda name, metric: ('{:.1f}'.format(state['jobs'][name][metric])
                                 if state['jobs'][name]['status'] == 'complete' and state['jobs'][name].get(metric) is not None else '—')
    lines = ['## AppWorld · ACE reproduction with Qwen3-8B', '',
        'A separate experiment from the four-corpus panel above: the released ace-appworld configurations and paper-era ACE agents, with only the language model replaced by Qwen3-8B (Q4_K_M, thinking off, context 32,768). One run per condition. TGC = task goal completion (all unit tests of a task pass); SGC = scenario goal completion (all tasks of a scenario pass); both from the official AppWorld evaluator. A dash means the condition has not finished; no partial-split value is reported.', '',
        '| **Method** | **GT** | **Test-Normal TGC ↑** | **Test-Normal SGC ↑** | **Test-Challenge TGC ↑** | **Test-Challenge SGC ↑** | **Status** |',
        '| --- | :---: | ---: | ---: | ---: | ---: | --- |']
    for method, gt_mark, pattern in APPWORLD_ROWS:
        normal, challenge = pattern.format('test_normal'), pattern.format('test_challenge')
        status = '; '.join('{} {}'.format(split.replace('test_', ''), state['jobs'][pattern.format(split)]['status'])
                           for split in ['test_normal', 'test_challenge'])
        lines.append('| {} | {} | {} | {} | {} | {} | {} |'.format(method, gt_mark,
            cell(normal, 'task_goal_completion'), cell(normal, 'scenario_goal_completion'),
            cell(challenge, 'task_goal_completion'), cell(challenge, 'scenario_goal_completion'), status))
    lines += ['', '**Paper reference, not our results:** Zhang et al. (ICLR 2026), Table 1, DeepSeek-V3.1 backbone.', '',
        '| **Method** | **GT** | **Test-Normal TGC** | **Test-Normal SGC** | **Test-Challenge TGC** | **Test-Challenge SGC** |',
        '| --- | :---: | ---: | ---: | ---: | ---: |']
    for (method, gt_mark), values in APPWORLD_PAPER.items():
        lines.append('| {} | {} | {} |'.format(method, gt_mark, ' | '.join('{:.1f}'.format(v) for v in values)))
    lines += ['', '**AppWorld progress**', '',
        '| **Job** | **Kind** | **Tasks started** | **Context exhausted** | **Status** | **Trained playbook** |',
        '| --- | --- | ---: | ---: | --- | --- |']
    for name, job in jobs.items():
        p = progress.get(name, {}); total = APPWORLD_SPLITS.get(job['split'], '?')
        playbook = '—'
        if job.get('final_playbook'):
            folder = storage/'appworld_ace_qwen/playbooks'/Path(job['final_playbook']).parent.name
            live = folder/'playbook.txt'
            if live.exists():
                bullets = sum(1 for x in live.read_text().splitlines() if x.lstrip().startswith('['))
                playbook = '{} ({} bullets)'.format(filelink('playbook.txt', live), bullets)
        lines.append('| `{}` | {} | {}/{} | {} | {} | {} |'.format(name.replace('qwen3_8b_', ''), job['kind'],
            p.get('tasks', 0), total, p.get('context_exhausted', 0), state['jobs'][name]['status'], playbook))
    lines += ['', 'Context exhausted counts model calls whose input did not fit the 32,768-token context; following the upstream generator, such a call returns an empty response and the input is never truncated. Deviations from the paper environment: Python 3.13 (changes traceback formatting shown to the agent), a one-line evaluator return-value compatibility patch, and the released configurations’ single offline epoch. Native-bridge revision r2 (decided 2026-09-15): a model response the local runtime leaves incomplete is retried up to three times and, if still incomplete, its partial text is passed to the agent; r1 stopped the shard instead. Only the three test_challenge shards that stopped on such a response were rerun; every other job had none, so its calls and scores are unchanged. Trained playbooks are mirrored under `Storage/appworld_ace_qwen/playbooks/`; snapshots every 30 tasks sit beside each live file.', '']
    return lines


def render(data, protocol, prep, output):
    all_rows = data['rows']
    now = datetime.datetime.now(datetime.timezone.utc)
    states = collections.Counter(status(r) for r in all_rows)
    invalid = counts(all_rows, 'attempted')-counts(all_rows, 'predicted')
    lines = ['# v5 results', '',
        '**Qwen3-8B (Q4_K_M) · Four corpora · 100 evaluation items per corpus · Seeds 42, 43, 44**', '',
        'Report generated: **{}**. This is a live internal experiment record; historical local/server scores are excluded.'.format(now.strftime('%Y-%m-%d %H:%M:%S UTC')), '',
        '| **Progress** | **Current / planned** |', '| --- | ---: |',
        '| Valid evaluation predictions | {:,} / 8,400 |'.format(counts(all_rows, 'predicted')),
        '| Evaluation attempts, including invalid outputs | {:,} / 8,400 |'.format(counts(all_rows, 'attempted')),
        '| Invalid evaluation outputs | {:,} |'.format(invalid),
        '| Memory updates, including offline training cycles | {:,} / 5,400 |'.format(memory_updates(all_rows)),
        '| Judgments | {:,} / 8,400 |'.format(counts(all_rows, 'judged')),
        '| Runs with 100 valid predictions | {} / 84 |'.format(sum(prediction_done(r) for r in all_rows)),
        '| Fully evaluated runs, including required updates and judgments | {} / 84 |'.format(sum(fully_done(r) for r in all_rows)), '',
        '**Run states:** '+ '; '.join('{} {}'.format(n, label.lower()) for label, n in sorted(states.items()))+'.', '',
        'A prediction-complete run still needs judging. Failed and held runs are explicit; they are not counted as completed. Full completion ETA remains unavailable while methods and judging are unstarted.', '',
        '## Experiment conditions', '',
        '- Each corpus uses **100 train/adaptation + 100 development + 100 evaluation** records. The panel contains 400 unique evaluation records, reused across methods and seeds; 8,400 is the planned number of prediction events.',
        '- The three repetitions reuse the same item set. Their SD describes run/order variation, not 300 independent evaluation examples per corpus.',
        '- Qwen3-8B Q4_K_M, thinking off, context 32,768; up to eight independent RTX A6000 streams. Online items remain serial within each run.',
        '- Learned-context cap: 4,096 tokens. Initial output caps: generator/optimizer/reflector 4,096; curator 8,192. Predeclared length-only retries apply; malformed adaptive outputs stop their condition after the allowed format retry.',
        '- GT ✓/✗ describes feedback used for adaptation. Online GT ✓ is revealed only after the current prediction is committed. Offline memory is learned from train, then frozen before evaluation.',
        '- The evaluation panel was previously observed. These are documented task transfers with stage-specific seals, not exact reproductions of the papers\' datasets or hyperparameters.', '',
        '## Main results', '',
        'Scores are percentages, shown as **mean ± sample SD across all three seeds** only when that metric is available for all three. `— (2/3)` means two seed scores exist but no partial-seed mean is reported. `N/A` means the metric does not apply. ΔAcc is the percentage-point difference from the matched Base mean.', '',
        'Acc uses all 100 evaluation attempts per seed, counting invalid outputs as incorrect. {}'.format(
            'For a seed with invalid outputs, Micro/Macro-F1 come from the validated all-attempt derivation `{}`: an invalid output predicts no label, adding a false negative for its reference label and no false positive, so the denominator is never reduced. The derivation reproduces the stage F1 exactly on all {} runs without invalid outputs. Seed detail marks these rows.'.format(
                data['derived_sources'][-1]['protocol'], data['derived_sources'][-1]['validation']['runs_without_invalid_outputs_checked'])
            if data.get('derived_sources') else
            'Other classification metrics remain unavailable for a seed with invalid outputs under the current exporter. Acc can therefore be available while the method run is incomplete. Per-seed details below expose this distinction.'), '']
    judges = data.get('judge_sources', [])
    if judges:
        judge = judges[-1]
        index = lines.index('## Experiment conditions')
        lines[index:index] = ['**Conformability judge:** `{}` (seal `{}`).{}{} Conformability is filled only for runs whose 100 judgments are all resolved; unresolved judgments are never imputed.'.format(
            judge['protocol'], judge['seal_sha256'][:12],
            ' **Same-family evaluation: the judge is the evaluated Qwen3-8B backbone.**' if judge.get('same_model_judge') else '',
            ' Provisional; human calibration not collected.' if judge.get('provisional') else ''), '']
    execution = data.get('execution', {})
    pointers = [p for p in [execution, data.get('optimization', {})] if p]
    if pointers:
        latest = max(pointers, key=lambda p: p['at'])
        index = lines.index('## Experiment conditions')
        lines[index:index] = ['**Latest stage:** `{}` — `{}` (status observed {}).'.format(
            latest.get('active_stage', '?'), latest.get('status', '?'), iso(latest['at'])), '']
    if execution:
        index = lines.index('## Experiment conditions')
        lines[index:index] = [
            'ACE/DC r1 production and r2 development are preserved as historical evidence. r3 passed all 18 development cases. Its 36 ACE trajectories remain current. A separate r4 revision replaces only the 18 DC trajectories after passing all six DC development cases. r2 admitted no production because DC repeated to the output limit. A lower selected-panel count after admission reflects fresh trajectories, not deleted evidence. Development predictions are excluded from evaluation totals.', '',
            'The revised generator format nests evidence under model-selected labels and makes abstention exclusive, then encodes those decisions into the unchanged canonical scoring format. DC retains the r3 serialization bounds: 1–24 complete description/example/usage-count items, with 160/320 Unicode-character text limits. Every model-authored item is rendered without trimming or deduplication. DC r4 additionally limits its generated explanation to 1600 Unicode characters to prevent repetitive answer narration; r3 ACE generation is unchanged. These are additional method-specific format constraints, so this is a documented task transfer rather than an exact free-form-curator reproduction. GT access, data/order, seeds, model, context/role token caps, the final 4096-token memory budget and scoring rules are unchanged. Base/ICL retains its original sealed output format.', '']
    if execution.get('recovery_revision'):
        index = lines.index('## Experiment conditions')
        lines[index:index] = [
            '**DC recovery execution revision:** `{}`. CaChe GT ✗ seed44 and GoEmotions GT ✓ seed44 resume from their preserved r4 checkpoints. Invalid Unicode surrogate strings are rejected through the existing single format retry before tokenization; incomplete responses retry within the existing three-attempt transport limit. Model, prompts, requested schemas, seeds, data order and budgets are unchanged. Original failed responses and GT-reveal receipts are retained; no model-written text is normalized or removed. Five recovery tests and validation of 36 cached development curator responses passed. Prefix audits are recorded separately.'.format(execution['recovery_revision']), '']
    retained = [r for r in all_rows if r.get('protocol') == 'four-corpus-server-v5-dc-retained-r5']
    if retained:
        index = lines.index('## Experiment conditions')
        lines[index:index] = [
            '**DC retained-update variant (`four-corpus-server-v5-dc-retained-r5`):** {} are selected from this separately reported DC variant. A verified unusable curator response is rejected and the prior memory is retained, instead of stopping the condition as the r4 fail-stop policy does. Per its revision record, seeds 42 and 43 are byte-for-byte imports of their complete r4 trajectories because no unusable curator response occurred in them; seed 44 continues its valid r4 prefix under the retained policy. Every other DC (CU) row remains r4 fail-stop. Seed detail marks these rows.'.format(
                ', '.join('{} GT {} seed {}'.format(dict(CORPORA)[r['cell']['dataset']], gt(r['cell']['adaptation_gt']), r['cell']['seed']) for r in retained)), '']
    if any(r.get('protocol') == 'four-corpus-server-v5-miprov2-r6' for r in all_rows):
        index = lines.index('## Experiment conditions')
        lines[index:index] = [
            '**MIPROv2 (`four-corpus-server-v5-miprov2-r6`):** pinned DSPy MIPROv2 on Dreaddit and GoEmotions, the two corpora with validated label GT. Candidate programs are selected by a full-development corpus F1 objective, macro for Dreaddit and micro for GoEmotions, over all 100 development records on every trial, with minibatching disabled, up to 30 trials and 10 instruction candidates. The selected program, bounded to eight demonstrations and the 4,096-token learned-context budget, is frozen and hashed before evaluation. Both seed-42 development cases passed before admission. A first development attempt that ran both cases in one process failed because the optimizer holds process-global runtime state. It is preserved, and every case now runs in its own process. Development evaluations are not memory updates and are excluded from the update total.', '']
    if any(r.get('protocol') == 'four-corpus-server-v5-gepa-r7' for r in all_rows):
        index = lines.index('## Experiment conditions')
        lines[index:index] = [
            '**GEPA (`four-corpus-server-v5-gepa-r7`):** pinned DSPy 3.0.3 GEPA with the GEPA 0.0.7 engine on Dreaddit and GoEmotions, with the v5 budget of 3,000 metric calls, including initialization and validation, and reflection minibatch 3. Reflection uses the same Qwen3-8B backbone at temperature 1.0, as in the documented DSPy configuration. GEPA searches with its native per-item scores, the F1 between reference and predicted label sets, and textual feedback naming reference, missed and unsupported labels. GEPA 0.0.7 averages per-item scores, so the final program is selected separately among its candidates by the same full-development corpus objective as MIPROv2, from recorded development predictions without additional calls. GEPA internals are unchanged. Both seed-42 development cases must pass before admission.', '']
    unstarted = [r for r in all_rows if r['state'].get('status', 'unstarted') == 'unstarted']
    unjudged = [r for r in all_rows if r not in unstarted and r['state'].get('judged', 0) < 100]
    remaining = []
    if unstarted:
        methods = sorted({METHODS[r['cell']['method']] for r in unstarted}, key=list(METHODS.values()).index)
        remaining.append('{} predictions are unstarted ({} seed runs)'.format('/'.join(methods), len(unstarted)))
    if unjudged:
        remaining.append('judging is incomplete for {} predicted runs'.format(len(unjudged)))
    if remaining:
        index = lines.index('## Experiment conditions')
        lines[index:index] = ['**Remaining work:** {}. Prediction completion does not launch later stages or mean that the full experiment is complete.'.format(
            '; '.join(remaining)), '']
    for corpus, title in CORPORA:
        lines += ['### '+title, '',
            '| **Phase** | **Method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **ΔAcc pp** | **Valid / 300** | **Status** |',
            '| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
        base = [r for r in all_rows if r['cell']['dataset'] == corpus and r['cell']['method'] == 'base']
        base_values = [final_value(r, 'accuracy') for r in base]
        for condition in [c for c in protocol['conditions'] if c['dataset'] == corpus]:
            rows = [r for r in all_rows if key(r['cell']) == key(condition)]
            task_scored = corpus in ['dreaddit', 'goemotions']
            values = [final_value(r, 'accuracy') for r in rows]
            delta = '{:+.2f}'.format(statistics.mean(values)-statistics.mean(base_values)) if task_scored and all(v is not None for v in values+base_values) else ('N/A' if not task_scored else '—')
            grouped = collections.Counter(status(r) for r in rows)
            state = '; '.join('{} {}'.format(n, label.lower()) for label, n in sorted(grouped.items()))
            metric = lambda name: aggregate(rows, name) if task_scored else 'N/A'
            lines.append('| {} | {} | {} | {} | {} | {} | {} | {} | {}/300 | {} |'.format(
                phase(condition['phase']), METHODS[condition['method']], gt(condition['adaptation_gt']),
                metric('accuracy'), metric('micro_f1'), metric('macro_f1'), aggregate(rows, 'conformability'),
                delta, counts(rows, 'predicted'), state))
        lines.append('')
    judging = 'provisional same-model judge' if judges else 'pending'
    lines += ['## Dataset-specific metric definitions', '',
        '| **Dataset** | **Accuracy** | **F1 / label conditions** | **Conformability** |',
        '| --- | --- | --- | --- |',
        '| Dreaddit | Binary exact-label accuracy against released stress labels | Micro/Macro-F1 over both classes; stress-class F1 and other binary metrics are in the source JSON when available | Source-grounding judgment, independent of classification correctness; {} |'.format(judging),
        '| GoEmotions | Exact-set accuracy over the 28 official labels | Multilabel Micro/Macro-F1; official neutral co-labels are preserved. Macro-F1 over all 28 labels differs from supported-label Macro-F1 | Same four-dimension v2 grounding rubric; {} |'.format(judging),
        '| CaChe | N/A: no validated label GT for the provisional thematic codebook | Label-reference F1 N/A. Model agreement is not substituted for accuracy | Source-only thematic grounding; {} |'.format(judging),
        '| ParlaMint-GB | N/A: no validated label GT for the provisional thematic codebook | Label-reference F1 N/A. These provisional topics are not CAP benchmark labels | Source-only thematic grounding; {} |'.format(judging), '',
        '**Conformability v2:** a method-blind, source-only judge scores factual support, evidence relevance, attribution, and material unsupported assertions on 0/1/2. A pass requires all four dimensions equal 2 and valid output/schema. {}'.format(
            'Scores come from the provisional same-model Qwen3-8B judge named above; a known invalid prediction is a resolved failure without a judge call.' if judges
            else 'The primary judge is not yet selected/calibrated, so no Conformability score is filled.'), '',
        'Literal exact-quote match and raw model-reported offset validity are separate mechanical diagnostics in the linked JSON reports. They are not Conformability. Partial quote statistics are not promoted to completed method scores.', '',
        '**Test-Normal TGC↑, Test-Normal SGC↑, Test-Challenge TGC↑, Test-Challenge SGC↑:** N/A for all four corpora; there are no corresponding AppWorld task-success evaluators, scenario groups, or official Normal/Challenge splits.', '',
        '**Other metrics:** available per-seed source reports contain applicable precision/recall/F1 variants, class-wise statistics, confusion matrices, and corpus-specific metrics. Confidence intervals, probability-based calibration/ranking, human review, complete cost telemetry, and other conditional registry entries remain pending or unavailable until their prerequisites and exporters are satisfied. Registering a metric is not evidence it was measured.', '',
        '## Per-seed results and progress', '',
        '`Pred` = valid / attempted evaluation outputs, with 100 planned per seed. `Train` = offline ACE adaptation attempts. `Upd` = committed memory-update cycles, including rejected oversized candidates that retain prior valid memory. `Active min` is per-run active time; simultaneous runs must not be summed as elapsed wall time.', '']
    for corpus, title in CORPORA:
        lines += ['### '+title+' — seed detail', '',
            '| **Phase / method** | **GT** | **Seed** | **Pred** | **Train** | **Upd** | **Judged** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conf %** | **Active min** | **Status** |',
            '| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
        for row in [r for r in all_rows if r['cell']['dataset'] == corpus]:
            c, s = row['cell'], row['state']
            number = lambda name: '{:.2f}'.format(final_value(row, name)) if final_value(row, name) is not None else '—'
            classification = lambda name: number(name) if corpus in ['dreaddit', 'goemotions'] else 'N/A'
            lines.append('| {} / {} | {} | {} | {}/{} | {} | {} | {}/100 | {} | {} | {} | {} | {} | {} |'.format(
                phase(c['phase']), METHODS[c['method']], gt(c['adaptation_gt']), c['seed'], s.get('predicted', 0), s.get('attempted', 0),
                s.get('adapted', 0) if c['phase'] == 'offline' and c['method'] == 'ace' else '—',
                s.get('updated', 0) if c['method'] in ['ace', 'dc_cu'] else '—', s.get('judged', 0),
                classification('accuracy'), classification('micro_f1'), classification('macro_f1'), number('conformability'),
                '{:.1f}'.format(s['active_seconds']/60) if 'active_seconds' in s else '—',
                status(row)+(' · retained DC variant' if row.get('protocol') == 'four-corpus-server-v5-dc-retained-r5' else '')
                +(' · F1 counts {} invalid as no label'.format(row['invalid_n']) if row.get('derived_f1') else '')))
        lines.append('')
    lines += appworld_lines(prep, prep.parent)
    lines += ['## Sources and refresh', '',
        'This file is regenerated from the following v5 metadata snapshots. The existing five-minute monitor refreshes the server mirrors and regenerates this file. Server stage reports refresh about every 20 seconds while their controller runs; this file is a periodic snapshot. Links below point to the local workspace mirrors. Original server artifacts are under `/home/sy23985/Storage/acl2027_server_v5_20260914`.', '']
    for source in data['sources']:
        lines.append('- {} — {}, seal `{}`.'.format(filelink(source['protocol'], Path(source['path'])), iso(source['report_updated_at']), source['seal_sha256']))
    for source in data.get('judge_sources', []):
        lines.append('- {} — judge, {}, seal `{}`.'.format(filelink(source['protocol'], Path(source['path'])), iso(source['report_updated_at']), source['seal_sha256']))
    for source in data.get('derived_sources', []):
        lines.append('- {} — derived metric, {}, validated on {} runs without invalid outputs.'.format(
            filelink(source['protocol'], Path(source['path'])), iso(source['report_updated_at']),
            source['validation']['runs_without_invalid_outputs_checked']))
    lines += ['', '- '+filelink('Machine-readable snapshot of the 84 planned runs', output.with_suffix('.snapshot.json')),
        '- '+filelink('Current execution status', prep/'STATUS.md'),
        '- '+filelink('Fixed v5 metric registry and applicability', prep.parent/'experiment_guidelines/four_corpus_server_v5/METRIC_REGISTRY.md'),
        '- '+filelink('Terminal progress viewer', prep/'TERMINAL_PROGRESS.md'), '',
        'Later revisions select the latest admitted result for each matching condition; repeats are not counted as independent runs. Source stage reports and older evidence remain preserved. No source excerpts, generated answers, GT labels, or playbooks are included here.', '']
    if data['notices']:
        lines += ['Import notices: '+ '; '.join(data['notices']), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prep', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = load(args.protocol)
    data = collect(args.prep, protocol)
    text = render(data, protocol, args.prep, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.output.with_suffix('.snapshot.json')
    snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    snapshot_path.chmod(0o600)
    args.output.write_text(text)
    print(json.dumps(dict(file=str(args.output), planned_rows=len(data['rows']),
        predicted=counts(data['rows'], 'predicted'), attempted=counts(data['rows'], 'attempted'),
        judged=counts(data['rows'], 'judged'), sources=len(data['sources']))))


if __name__ == '__main__':
    main()
