"""Prepare, preflight, seal, dispatch and report a separate ACE/DC stage."""
from pathlib import Path
import argparse, concurrent.futures, fcntl, hashlib, json, os, subprocess, sys, time
from core import Native, atomic, digest, load, rows
from run import execute, verify
from adapters import Upstream


def identity(pid):
    try: return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19]
    except FileNotFoundError: return None


def prepare(parent, stage):
    if (stage/'manifest.json').exists(): raise RuntimeError('Stage is sealed')
    base = load(parent/'prediction_manifest.json')
    cells, orders = [], {}
    for corpus in ['dreaddit', 'goemotions', 'cache', 'parlamint_gb']:
        orders[corpus] = {}
        for seed in [42, 43, 44]:
            training = rows(parent/'data'/corpus/'train.jsonl')
            adaptation = sorted([r['record_id'] for r in training],
                key=lambda rid: hashlib.sha256(f'v5-adaptation:{seed}:{rid}'.encode()).hexdigest())
            orders[corpus][str(seed)] = dict(adaptation=adaptation,
                evaluation=load(parent/'orders.json')[corpus][str(seed)])
            for phase, method in [('offline', 'ace'), ('online', 'ace'), ('online', 'dc_cu')]:
                for gt in (['yes', 'no'] if corpus in ['dreaddit', 'goemotions'] else ['no']):
                    cells.append(dict(id=f'{corpus}__{phase}__{method}__gt_{gt}__seed{seed}',
                        dataset=corpus, phase=phase, method=method, adaptation_gt=gt, seed=seed, n=100))
    # Interleave datasets and GT regimes, keeping streams serial and seeds independent.
    cells.sort(key=lambda c: (c['seed'], ['online', 'offline'].index(c['phase']),
                             c['method'], c['adaptation_gt'], c['dataset']))
    plan = dict(protocol='four-corpus-server-v5-adaptation-r1', parent=str(parent),
        parent_prediction_seal=base['seal_sha256'], runtime=base['runtime'], cells=cells,
        task_transfer=dict(output='Original generator reasoning/final_answer mapped to the frozen common explanation/label_ids/evidence schema; original prompts plus explicit format mapping.',
            ace='Original generator, GT/no-GT reflector and curator prompts; unchanged pinned playbook function ASTs; ADD only, stable IDs and helpful/harmful counters; one reflection and curation per item; no dedup analyzer.',
            dc='Unchanged pinned advanced_generate function AST, DynamicCheatsheet_Cumulative, one round, provider generation overridden by the common native runtime; no code execution. Validate wrapper before upstream extraction; never silently retain malformed output.',
            gt='Current GT read only after durable prediction commit; no labels or evaluator feedback in GT-no. No current or future GT supplied to prediction.',
            memory='4096 tokenizer tokens; reject complete oversized candidates and retain prior state, with a logged rejected update.',
            failures='One identical format retry. Exhausted adaptive prediction/update fails the condition; offline frozen evaluation records invalid outputs and continues. No test-output repair.',
            restart='Immutable per-item prediction and update commits; replay checkpoints and request cache to resume without duplicate updates.',
            dependencies='Only unchanged upstream function ASTs/constants execute; provider initializers, dotenv and external-client imports do not execute.',
            concurrency='Eight independent GPU streams, one request at a time per stream; throughput profile, not single-GPU reference timing.'),
        judge=None, full_panel_runs=84, stage_runs=54, stage_predictions=5400,
        development_gate='Only corpus/phase/method/GT conditions passing both development-source probes are admitted; all three seeds share this gate. Failed probes remain pending in a separate revision.')
    atomic(stage/'orders.json', orders)
    atomic(stage/'plan.json', plan)
    print(json.dumps({'prepared_runs': len(cells), 'prediction_target': 5400}))


def report(stage):
    from report_predictions import scores
    plan = load(stage/'plan.json'); parent = Path(plan['parent']); tasks = load(parent/'tasks.json')
    result = []
    for cell in plan['cells']:
        directory = stage/'runs'/cell['id']
        state = load(directory/'state.json') if (directory/'state.json').exists() else {'status': 'queued'}
        predictions = [load(p) for p in sorted(directory.glob('prediction_*.json'))]
        updates = [load(p) for p in sorted((directory/'updates').glob('*.json'))]
        if cell['dataset'] in ['dreaddit', 'goemotions']:
            gold = {r['record_id']: r for r in rows(parent/'data'/cell['dataset']/'test.jsonl')}
            metric = scores(predictions, gold, tasks[cell['dataset']])
        else: metric = {'accuracy': None, 'accuracy_status': 'not_applicable_no_reference'}
        anchors = [a for p in predictions if p['valid'] for a in p['literal_anchors']]
        metric.update(conformability=None, conformability_status='pending_judge_selection',
            submitted_quotes=len(anchors),
            literal_exact_quote_validity=100*sum(a['literal_match'] for a in anchors)/len(anchors) if anchors else None,
            reported_offset_validity=100*sum(a['reported_offset_valid'] for a in anchors)/len(anchors) if anchors else None,
            rejected_memory_updates=sum(not u['accepted'] for u in updates),
            final_memory_tokens=updates[-1]['memory_tokens'] if updates else 0)
        atomic(directory/'metrics.json', metric)
        result.append(dict(cell=cell, state=state, metrics=metric))
    overview = dict(protocol=plan['protocol'], scope='ACE/DC stage: 54 runs of the 84-run panel',
        predicted=sum(r['state'].get('predicted', 0) for r in result),
        attempted=sum(r['state'].get('attempted', 0) for r in result),
        adapted=sum(r['state'].get('adapted', 0) for r in result),
        updated=sum(r['state'].get('updated', 0) for r in result), stage_prediction_target=5400,
        judged=0, updated_at=time.time(), rows=result)
    atomic(stage/'results.json', overview)
    lines = ['# Qwen3-8B ACE/DC adaptation stage', '',
        f'Updated UTC: {time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}. Valid predictions {overview["predicted"]}/5400. Judgments pending.', '',
        '54 ACE/DC seed runs. Base/ICL is a separate preserved stage; MIPROv2/GEPA remain pending. No historical scores are imported.', '',
        '| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Updates** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |']
    for r in result:
        c, s, m = r['cell'], r['state'], r['metrics']
        fmt = lambda k: f'{m[k]:.2f}' if m.get(k) is not None else '—'
        acc = 'N/A' if c['dataset'] in ['cache', 'parlamint_gb'] else fmt('accuracy')
        lines.append(f'| {c["dataset"]} | {c["phase"]} | {c["method"]} | {c["adaptation_gt"]} | {c["seed"]} | {s.get("predicted",0)}/100 | {s.get("updated",0)}/100 | {acc} | {fmt("micro_f1")} | {fmt("macro_f1")} | PENDING | {s.get("active_seconds",0)/60:.1f} | {s["status"]} |')
    lines += ['', 'GT is adaptation feedback. Online GT is revealed only after the current prediction is committed. Offline updates use train only; the final playbook is frozen before evaluation. Invalid/failed rows are not completed experiment rows.', '',
              'Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. CaChe/ParlaMint have no validated label GT. Conformability awaits judge selection. Quote matching is a separate mechanical metric.', '',
              'Complete oversized memory proposals are rejected with the prior state retained. Malformed or exhausted adaptive responses stop their condition. The 4096-token memory cap and common role caps match the Base/ICL runtime.']
    (stage/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    (stage/'METRICS.md').write_text('# Adaptation-stage metrics\n\nPer-cell metrics are in results.json and runs/*/metrics.json. Counts, failures and dataset-specific definitions appear in RESULTS.md. Conformability and conditional registry metrics are not yet final.\n')
    return {k: v for k, v in overview.items() if k != 'rows'}


def preflight(stage):
    from transformers import AutoTokenizer  # Resolve lazy imports before threads.
    plan = load(stage/'plan.json'); parent = Path(plan['parent'])
    cells = [c for c in plan['cells'] if c['seed'] == 42]
    upstream = Upstream(stage/'upstream')
    def group(gpu):
        values = []
        for cell in cells[gpu::8]:
            try:
                native = Native(stage/'preflight'/cell['id']/'calls', f'http://127.0.0.1:{11840+gpu}', plan['runtime']['tokenizer'], 42)
                execute(parent, stage, cell, native, upstream, dev=True)
                state = load(stage/'preflight'/cell['id']/'state.json')
                values.append({'cell': cell['id'], 'status': state['status'], 'predicted': state['predicted'], 'updated': state['updated']})
            except Exception as exc:
                values.append({'cell': cell['id'], 'status': 'failed', 'error_type': type(exc).__name__})
            atomic(stage/'preflight'/f'gpu_{gpu}.json', values)
        return values
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        values = [v for group_results in pool.map(group, range(8)) for v in group_results]
    summary = dict(cases=len(values), passed=sum(v['status'] == 'prediction_complete' for v in values),
                   results=values, data_split='development only; shortest and longest source per corpus', updated_at=time.time())
    atomic(stage/'preflight/report.json', summary)
    print(json.dumps(summary))


def seal(stage):
    if (stage/'manifest.json').exists(): raise RuntimeError('Stage already sealed')
    plan = load(stage/'plan.json'); parent = Path(plan['parent'])
    probes = load(stage/'preflight/report.json')
    if probes['cases'] != 18: raise RuntimeError('Development preflight is incomplete')
    passed = {r['cell'].rsplit('__seed', 1)[0] for r in probes['results'] if r['status'] == 'prediction_complete'}
    admitted = [c for c in plan['cells'] if c['id'].rsplit('__seed', 1)[0] in passed]
    if not admitted: raise RuntimeError('No condition passed the development gate')
    tests = load(stage/'tests.json')
    if not tests['passed']: raise RuntimeError('Behavior checks are incomplete')
    files = list((stage/'code').glob('*.py')) + list((stage/'upstream').rglob('*'))
    files += [stage/'plan.json', stage/'orders.json', stage/'preflight/report.json', stage/'tests.json']
    files += [parent/p for p in load(parent/'prediction_manifest.json')['files']]
    manifest = dict(plan, files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},
                    preflight_cases=18, sealed_at=time.time(), admitted_cells=admitted,
                    withheld_cells=[c['id'] for c in plan['cells'] if c not in admitted])
    manifest['seal_sha256'] = digest(manifest)
    atomic(stage/'manifest.json', manifest)
    print(json.dumps({'admitted_runs': len(admitted), 'withheld_runs': len(manifest['withheld_cells']), 'sha256': manifest['seal_sha256']}))


def launch(stage):
    manifest = verify(stage); parent = Path(manifest['parent'])
    controller_lock = (stage/'controller.lock').open('a')
    fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Also exclude the earlier prediction controller and any other adaptation controller.
    shared_lock = (parent/'prediction_controller.lock').open('a')
    fcntl.flock(shared_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ownership = load(parent/'services/ownership.json')['services']
    for service in ownership:
        assert identity(service['pid']) == service['start_identity'], 'Owned service identity changed'
    for p in (parent/'runs').glob('*/worker.json'):
        prior = load(p)
        if identity(prior['pid']) == prior['start_identity']: raise RuntimeError('Prior stage worker is still alive')
    queue, finished, active = [], {}, {}
    for cell in manifest['admitted_cells']:
        directory = stage/'runs'/cell['id']; directory.mkdir(parents=True, exist_ok=True)
        if (directory/'worker.json').exists():
            prior = load(directory/'worker.json')
            if identity(prior['pid']) == prior['start_identity']: raise RuntimeError('Existing live worker needs recovery')
        state = load(directory/'state.json') if (directory/'state.json').exists() else {}
        if state.get('status', '').startswith('prediction_complete') or state.get('status') == 'failed':
            finished[cell['id']] = state['status']
        else: queue.append(cell)
    for cell_id in manifest['withheld_cells']:
        cell = next(c for c in manifest['cells'] if c['id'] == cell_id)
        atomic(stage/'runs'/cell_id/'state.json', dict(condition_id=cell_id, dataset=cell['dataset'],
            method=cell['method'], phase=cell['phase'], adaptation_gt=cell['adaptation_gt'], seed=cell['seed'],
            status='withheld_failed_development_probe', predicted=0, attempted=0, updated=0, adapted=0, judged=0,
            updated_at=time.time()))
    last_report = 0
    while queue or active:
        stop = (stage/'STOP').exists() or (parent/'STOP').exists()
        listing = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True)
        for service in ownership:
            gpu = service['gpu']
            if stop or not queue or gpu in active: continue
            foreign = False
            for line in listing.splitlines():
                parts = [x.strip() for x in line.split(',')]
                if len(parts) != 2 or parts[0] != service['uuid']: continue
                try: environ = Path(f'/proc/{int(parts[1])}/environ').read_bytes()
                except (PermissionError, FileNotFoundError): foreign = True; continue
                if f'OLLAMA_HOST=127.0.0.1:{11840+gpu}'.encode() not in environ: foreign = True
            if foreign: continue
            cell = queue.pop(0); directory = stage/'runs'/cell['id']
            env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
                       PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(stage/'code')+os.pathsep+str(parent/'code'))
            with (directory/'worker.log').open('ab') as log:
                proc = subprocess.Popen([manifest['runtime']['python'], str(stage/'code/run.py'), '--stage', str(stage),
                    '--cell', cell['id'], '--gpu', str(gpu)], env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=log, start_new_session=True)
            atomic(directory/'worker.json', dict(pid=proc.pid, start_identity=identity(proc.pid), gpu=gpu, started_at=time.time()))
            active[gpu] = (proc, cell)
        for gpu, (proc, cell) in list(active.items()):
            code = proc.poll()
            if code is not None:
                statepath = stage/'runs'/cell['id']/'state.json'
                finished[cell['id']] = load(statepath)['status'] if statepath.exists() else 'worker_failed_before_state'
                del active[gpu]
        atomic(stage/'queue.json', dict(total_runs=54, queued=len(queue), active={str(g): c['id'] for g, (p, c) in active.items()},
            finished=finished, stop_requested=stop, updated_at=time.time(),
            status='running' if active or queue and not stop else 'paused' if stop else 'complete'))
        if time.monotonic()-last_report > 20 or not active:
            try: report(stage)
            except Exception as exc:
                atomic(stage/'report_error.json', dict(error_type=type(exc).__name__, at=time.time()))
            last_report = time.monotonic()
        if stop and not active: break
        time.sleep(3)
    report(stage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'preflight', 'seal', 'launch', 'report'])
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--parent', type=Path)
    args = parser.parse_args(); os.umask(0o077)
    if args.action == 'prepare': prepare(args.parent, args.stage)
    elif args.action == 'report': print(json.dumps(report(args.stage)))
    else: globals()[args.action](args.stage)
