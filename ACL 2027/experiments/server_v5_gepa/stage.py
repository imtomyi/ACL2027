"""Prepare, preflight, seal, dispatch and report the offline GEPA stage."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, subprocess, time
from core import atomic, digest, load, rows
from run import verify

DATASETS = ['dreaddit', 'goemotions']
SEEDS = [42, 43, 44]
PROBE_N = 6


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except FileNotFoundError: return None


def assert_idle_owned_services(parent):
    ownership = load(parent/'services/ownership.json')['services']
    for service in ownership:
        if identity(service['pid']) != service['start_identity']:
            raise RuntimeError('Owned service identity changed')
    for directory in [parent/'runs'] + list((parent/'stages').glob('*/runs')):
        for path in directory.glob('*/worker.json'):
            prior = load(path)
            if identity(prior['pid']) == prior['start_identity']:
                raise RuntimeError('Existing worker is live; wait for its safe checkpoint')
    listing = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True)
    selected = {s['uuid']: s for s in ownership}
    for line in listing.splitlines():
        parts = [x.strip() for x in line.split(',')]
        if len(parts) != 2 or parts[0] not in selected: continue
        service = selected[parts[0]]
        try: environ = Path(f'/proc/{int(parts[1])}/environ').read_bytes().split(b'\0')
        except FileNotFoundError: continue
        except PermissionError: raise RuntimeError('GPU has a process outside experiment ownership')
        if f'OLLAMA_HOST=127.0.0.1:{11840+service["gpu"]}'.encode() not in environ:
            raise RuntimeError('GPU has a process outside experiment ownership')
    return ownership


def optimizer_pins():
    import importlib, importlib.metadata as metadata, inspect
    modules = ['dspy.teleprompt.gepa.gepa', 'dspy.teleprompt.gepa.gepa_utils', 'gepa.api', 'gepa.core.engine', 'gepa.core.state']
    return dict(dspy=metadata.version('dspy'), gepa=metadata.version('gepa'), litellm=metadata.version('litellm'),
                module_sha256={m: hashlib.sha256(inspect.getsource(importlib.import_module(m)).encode()).hexdigest() for m in modules})


def prepare(parent, stage):
    if (stage/'manifest.json').exists(): raise RuntimeError('Stage is sealed')
    base = load(parent/'prediction_manifest.json')
    evaluation = load(parent/'orders.json')
    predecessor = load(parent/'stages/adaptation_r1/orders.json')
    cells, orders = [], {}
    for corpus in DATASETS:
        orders[corpus] = {}
        for seed in SEEDS:
            order = evaluation[corpus][str(seed)]
            if order != predecessor[corpus][str(seed)]['evaluation']:
                raise RuntimeError('The stage must retain the established evaluation order')
            orders[corpus][str(seed)] = dict(evaluation=order)
            cells.append(dict(id=f'{corpus}__offline__gepa__gt_yes__seed{seed}', dataset=corpus,
                              phase='offline', method='gepa', adaptation_gt='yes', seed=seed, n=len(order)))
    # Dreaddit is dispatched first by user priority; the scientific settings are identical for both corpora.
    cells.sort(key=lambda c: (c['dataset'] != 'dreaddit', c['seed'], c['dataset']))
    plan = dict(protocol='four-corpus-server-v5-gepa-r7', parent=str(parent),
        parent_prediction_seal=base['seal_sha256'], runtime=base['runtime'], cells=cells,
        optimizer_pins=optimizer_pins(),
        budget=dict(max_metric_calls=3000, reflection_minibatch_size=3, train_n=100, development_n=100,
                    basis='v5 GUIDELINES method budget: 3,000 metric calls including initialization/validation, reflection minibatch 3'),
        task_transfer=dict(
            output='Model wire output nests evidence within each selected label. Deterministic encoding produces the unchanged canonical label_ids/explanation/evidence/bullet_ids fields, retaining all model-selected labels and quotes. Coding and insufficient_context are mutually exclusive schema branches. No label is guessed, dropped, or repaired using GT.',
            gepa='Pinned DSPy GEPA and GEPA package, with module sources recorded in optimizer_pins. Task generation and reflection both use the common native Qwen3-8B runtime through a single-output local LM; no external provider client is constructed. Reflection uses temperature 1.0 as in the documented DSPy GEPA configuration; task generation uses temperature 0. Upstream defaults are retained for Pareto candidate selection, merge and perfect-score skipping. GEPA search uses its native per-item scores: item F1 between the reference and predicted label sets, which equals exact match for single-label Dreaddit, with textual feedback naming the reference labels and each missed or unsupported label. Because GEPA 0.0.7 aggregates per-item scores by arithmetic mean, the final program is selected separately among GEPA candidates by the registered full-development corpus objective, macro-F1 for Dreaddit and micro-F1 for GoEmotions, computed from that candidate\'s recorded predictions on all 100 development records, with no additional model calls. Ties are broken by the GEPA mean score and then by the earlier candidate. GEPA internals are not modified. A candidate whose learned context exceeds the 4096-token budget produces an invalid output without model calls and scores zero.',
            gt='Train and development GT are read during optimization only. The selected program is frozen and hashed before any evaluation input is read, and no evaluation GT reaches prediction.',
            memory='The learned context is bounded by the shared 4096-tokenizer-token budget that applies to the Base/ICL and adaptation runtimes.',
            failures='Exhausted format failures are recorded as invalid evaluation outputs and evaluation continues. An invalid development prediction scores zero in GEPA search, and any invalid development prediction sets a candidate\'s corpus objective to zero rather than gaining from abstention. No test-output repair.',
            restart='Immutable per-item evaluation commits, a saved compiled program, the GEPA run directory, an append-only prediction ledger and a request cache resume a run without repeating optimization.',
            dependencies='Only the installed pinned DSPy and GEPA optimizers execute; provider initializers, dotenv and external-client imports do not execute.',
            concurrency='Independent one-GPU streams, one request at a time per stream; throughput profile, not single-GPU reference timing.'),
        judge=None, full_panel_runs=84, stage_runs=len(cells),
        stage_predictions=sum(c['n'] for c in cells), development_probe_n=PROBE_N,
        predecessor='Base/ICL prediction stage, adaptation r3/r4/r5 and MIPROv2 r6; no trajectory, program or score is imported',
        development_gate='Both seed-42 conditions must complete six development sources end to end under a 30-metric-call probe budget, with a selected program and six valid predictions, before any production seed run is admitted.')
    atomic(stage/'orders.json', orders)
    atomic(stage/'plan.json', plan)
    print(json.dumps({'prepared_runs': len(cells), 'prediction_target': plan['stage_predictions']}))


def report(stage):
    from report_predictions import scores
    plan = load(stage/'plan.json'); parent = Path(plan['parent']); tasks = load(parent/'tasks.json')
    result = []
    for cell in plan['cells']:
        directory = stage/'runs'/cell['id']
        state = load(directory/'state.json') if (directory/'state.json').exists() else {'status': 'queued'}
        predictions = [load(p) for p in sorted(directory.glob('prediction_*.json'))]
        gold = {r['record_id']: r for r in rows(parent/'data'/cell['dataset']/'test.jsonl')}
        metric = scores(predictions, gold, tasks[cell['dataset']])
        anchors = [a for p in predictions if p['valid'] for a in p['literal_anchors']]
        optimization = load(directory/'optimization.json') if (directory/'optimization.json').exists() else {}
        metric.update(conformability=None, conformability_status='pending_judge_selection',
            submitted_quotes=len(anchors),
            literal_exact_quote_validity=100*sum(a['literal_match'] for a in anchors)/len(anchors) if anchors else None,
            reported_offset_validity=100*sum(a['reported_offset_valid'] for a in anchors)/len(anchors) if anchors else None,
            metric_calls=optimization.get('evaluated_items'),
            full_development_evaluations=optimization.get('full_development_evaluations'),
            development_objective=optimization.get('objective'),
            candidates=optimization.get('candidates'), selected_index=optimization.get('selected_index'),
            gepa_best_index=optimization.get('gepa_best_index'),
            selected_corpus_objective=optimization.get('selected_corpus_objective'),
            learned_context_tokens=optimization.get('learned_context_tokens'))
        atomic(directory/'metrics.json', metric)
        result.append(dict(cell=cell, state=state, metrics=metric))
    overview = dict(protocol=plan['protocol'], scope='Offline GEPA, two GT-bearing corpora, three seeds',
        predicted=sum(r['state'].get('predicted', 0) for r in result),
        attempted=sum(r['state'].get('attempted', 0) for r in result),
        metric_calls=sum(r['metrics'].get('metric_calls') or 0 for r in result),
        stage_prediction_target=plan['stage_predictions'], judged=0, updated_at=time.time(), rows=result)
    atomic(stage/'results.json', overview)
    lines = ['# Qwen3-8B offline GEPA stage', '',
        f'Updated UTC: {time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}. Valid predictions {overview["predicted"]}/{plan["stage_predictions"]}. Judgments pending.', '',
        'Pinned DSPy GEPA over the frozen train and development splits of the two corpora that carry validated label GT, with a 3,000-metric-call budget and reflection minibatch 3. GEPA searches with its native per-item scores and label feedback. The final program is selected among GEPA candidates by the full-development corpus F1 objective, computed from recorded development predictions without additional calls, then frozen and hashed before evaluation begins. CaChe and ParlaMint-GB have no validated label GT and are outside this stage.', '',
        '| **Dataset** | **Phase** | **Method** | **GT** | **Seed** | **Predicted** | **Candidates** | **Metric calls** | **Selected / GEPA best** | **Dev objective %** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |']
    for r in result:
        c, s, m = r['cell'], r['state'], r['metrics']
        fmt = lambda k: f'{m[k]:.2f}' if m.get(k) is not None else '—'
        count = lambda v: str(v) if v is not None else '—'
        lines.append(f'| {c["dataset"]} | {c["phase"]} | {c["method"]} | {c["adaptation_gt"]} | {c["seed"]} | '
                     f'{s.get("predicted",0)}/{c["n"]} | {count(m.get("candidates"))} | {count(m.get("metric_calls"))} | '
                     f'{count(m.get("selected_index"))} / {count(m.get("gepa_best_index"))} | {fmt("selected_corpus_objective")} | '
                     f'{fmt("accuracy")} | {fmt("micro_f1")} | {fmt("macro_f1")} | PENDING | {s.get("active_seconds",0)/60:.1f} | {s["status"]} |')
    lines += ['', 'GT is optimization feedback. Train and development labels are read during candidate search only, and the frozen program is hashed before the first evaluation input is read. Invalid/failed rows are not completed experiment rows.', '',
              'Dreaddit Acc is binary accuracy; GoEmotions Acc is exact-set accuracy over all 28 official labels, including allowed neutral co-labels. The development objective is macro-F1 for Dreaddit and micro-F1 for GoEmotions, computed over the complete development split. Conformability awaits judging. Quote matching is a separate mechanical metric.', '',
              'Selected / GEPA best compares the candidate chosen by the corpus objective with the candidate GEPA ranks first by mean per-item score. Metric calls include initialization, minibatch and full-development evaluations. A candidate exceeding the shared 4096-token learned-context budget produces invalid outputs without model calls.']
    (stage/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    (stage/'METRICS.md').write_text('# Optimization-stage metrics\n\nPer-cell metrics are in results.json and runs/*/metrics.json. Counts, failures and dataset-specific definitions appear in RESULTS.md. Conformability and conditional registry metrics are not yet final.\n')
    return {k: v for k, v in overview.items() if k != 'rows'}


def preflight(stage):
    plan = load(stage/'plan.json'); parent = Path(plan['parent'])
    shared_lock = (parent/'prediction_controller.lock').open('a')
    fcntl.flock(shared_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert_idle_owned_services(parent)
    from transformers import AutoTokenizer  # Resolve lazy imports before threads.
    if optimizer_pins() != plan['optimizer_pins']: raise RuntimeError('Pinned optimizer changed since preparation')
    cells = [c for c in plan['cells'] if c['seed'] == 42]
    code_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (stage/'code').glob('*.py')}
    atomic(stage/'preflight/execution.json', dict(code_sha256=code_hashes, optimizer_pins=plan['optimizer_pins'],
                                                 started_at=time.time(), development_only=True))
    # The optimizer holds module-level runtime state and DSPy settings are process-global,
    # so each development case runs in its own process on its own GPU stream.
    ownership = load(parent/'services/ownership.json')['services']
    workers = []
    for cell, service in zip(cells, ownership):
        directory = stage/'preflight'/cell['id']; directory.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
                   PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(stage/'code')+os.pathsep+str(parent/'code'))
        with (directory/'worker.log').open('ab') as log:
            proc = subprocess.Popen([plan['runtime']['python'], str(stage/'code/run.py'), '--stage', str(stage),
                '--cell', cell['id'], '--gpu', str(service['gpu']), '--dev'], env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        workers.append((cell, service['gpu'], proc))
    values = []
    for cell, gpu, proc in workers:
        code = proc.wait()
        statepath = stage/'preflight'/cell['id']/'state.json'
        state = load(statepath) if statepath.exists() else {}
        values.append({'cell': cell['id'], 'gpu': gpu, 'exit_code': code,
                       'status': state.get('status', 'worker_failed_before_state'),
                       'predicted': state.get('predicted', 0), 'demos': state.get('demos'),
                       'development_evaluations': state.get('updated', 0),
                       'error_type': state.get('error_type')})
        atomic(stage/'preflight/progress.json', values)
    probe_n = plan['development_probe_n']
    summary = dict(cases=len(values),
                   passed=sum(v['exit_code'] == 0 and v['status'] == 'prediction_complete'
                              and v['predicted'] == probe_n and v.get('demos') is not None for v in values),
                   results=values, data_split='development only; six sources per case, including shortest and longest plus four ID-hash-selected sources; optimization uses separate ID-hash-selected train and development subsets',
                   updated_at=time.time())
    atomic(stage/'preflight/report.json', summary)
    shared_lock.close()
    print(json.dumps(summary))


def seal(stage):
    if (stage/'manifest.json').exists(): raise RuntimeError('Stage already sealed')
    plan = load(stage/'plan.json'); parent = Path(plan['parent'])
    probes = load(stage/'preflight/report.json')
    if probes['cases'] != len(DATASETS) or probes['passed'] != len(DATASETS):
        raise RuntimeError('Both development cases must pass before production admission')
    passed = {r['cell'].rsplit('__seed', 1)[0] for r in probes['results'] if r['status'] == 'prediction_complete'}
    admitted = [c for c in plan['cells'] if c['id'].rsplit('__seed', 1)[0] in passed]
    if not admitted: raise RuntimeError('No condition passed the development gate')
    tests = load(stage/'tests.json')
    if not tests['passed']: raise RuntimeError('Behavior checks are incomplete')
    if optimizer_pins() != plan['optimizer_pins']: raise RuntimeError('Pinned optimizer changed before sealing')
    files = list((stage/'code').glob('*.py'))
    for filename, checksum in load(stage/'preflight/execution.json')['code_sha256'].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != checksum:
            raise RuntimeError('Preflight code changed after its execution began')
    files += [stage/'plan.json', stage/'orders.json', stage/'preflight/report.json', stage/'tests.json',
              stage/'preflight/execution.json', stage/'REVISION.json']
    files += [parent/p for p in load(parent/'prediction_manifest.json')['files']]
    manifest = dict(plan, files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},
                    preflight_cases=probes['cases'], sealed_at=time.time(), admitted_cells=admitted,
                    withheld_cells=[c['id'] for c in plan['cells'] if c not in admitted])
    manifest['seal_sha256'] = digest(manifest)
    atomic(stage/'manifest.json', manifest)
    print(json.dumps({'admitted_runs': len(admitted), 'withheld_runs': len(manifest['withheld_cells']), 'sha256': manifest['seal_sha256']}))


def launch(stage):
    manifest = verify(stage); parent = Path(manifest['parent'])
    controller_lock = (stage/'controller.lock').open('a')
    fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    shared_lock = (parent/'prediction_controller.lock').open('a')
    fcntl.flock(shared_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ownership = assert_idle_owned_services(parent)
    pending, finished, active = [], {}, {}
    for cell in manifest['admitted_cells']:
        directory = stage/'runs'/cell['id']; directory.mkdir(parents=True, exist_ok=True)
        if (directory/'worker.json').exists():
            prior = load(directory/'worker.json')
            if identity(prior['pid']) == prior['start_identity']: raise RuntimeError('Existing live worker needs recovery')
        state = load(directory/'state.json') if (directory/'state.json').exists() else {}
        if state.get('status', '').startswith('prediction_complete') or state.get('status') == 'failed':
            finished[cell['id']] = state['status']
        else: pending.append(cell)
    for cell_id in manifest['withheld_cells']:
        cell = next(c for c in manifest['cells'] if c['id'] == cell_id)
        atomic(stage/'runs'/cell_id/'state.json', dict(condition_id=cell_id, dataset=cell['dataset'],
            method=cell['method'], phase=cell['phase'], adaptation_gt=cell['adaptation_gt'], seed=cell['seed'],
            status='withheld_failed_development_probe', predicted=0, attempted=0, updated=0, adapted=0, judged=0,
            updated_at=time.time()))
    last_report = 0
    while pending or active:
        stop = (stage/'STOP').exists() or (parent/'STOP').exists()
        listing = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True)
        for service in ownership:
            gpu = service['gpu']
            if stop or not pending or gpu in active: continue
            foreign = False
            for line in listing.splitlines():
                parts = [x.strip() for x in line.split(',')]
                if len(parts) != 2 or parts[0] != service['uuid']: continue
                try: environ = Path(f'/proc/{int(parts[1])}/environ').read_bytes()
                except (PermissionError, FileNotFoundError): foreign = True; continue
                if f'OLLAMA_HOST=127.0.0.1:{11840+gpu}'.encode() not in environ: foreign = True
            if foreign: continue
            cell = pending.pop(0); directory = stage/'runs'/cell['id']
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
        atomic(stage/'queue.json', dict(total_runs=len(manifest['admitted_cells']), queued=len(pending),
            active={str(g): c['id'] for g, (p, c) in active.items()}, finished=finished, stop_requested=stop,
            updated_at=time.time(),
            status='running' if active or pending and not stop else 'paused' if stop else 'complete'))
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
