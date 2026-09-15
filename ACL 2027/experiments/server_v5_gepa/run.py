"""Offline GEPA: compile on GT-bearing train/development, freeze, then evaluate."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, time
from core import Native, atomic, load, rows, digest, evidence_checks, question
from predict_stage import literal_anchors
from output_contract import generate as generate_canonical, FORMAT
from gepa_optimizer import compile_program
from optimizer import learned_context


def verify(stage):
    manifest = load(stage/'manifest.json')
    if manifest['seal_sha256'] != digest({k: v for k, v in manifest.items() if k != 'seal_sha256'}):
        raise RuntimeError('Optimization manifest digest mismatch')
    for filename, checksum in manifest['files'].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != checksum:
            raise RuntimeError('Optimization source seal changed: ' + filename)
    return manifest


def probe_sources(native, records, probe_n, tag):
    """Extreme lengths plus deterministic additional development sources, never test inputs."""
    sources = {r['record_id']: r for r in records}
    ordered = sorted(sources, key=lambda rid: (len(native.tokenizer.encode(sources[rid]['text'])), rid))
    order = [ordered[0], ordered[-1]]
    extra = sorted([rid for rid in ordered if rid not in order],
                   key=lambda rid: hashlib.sha256((tag+':'+rid).encode()).hexdigest())
    order += extra[:max(0, probe_n-2)]
    if len(order) != probe_n: raise RuntimeError('Insufficient development probe sources')
    return order, sources


def execute(parent, stage, cell, native, dev=False, probe_n=6):
    directory = stage/('preflight' if dev else 'runs')/cell['id']
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory/'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    task = dict(load(parent/'tasks.json')[cell['dataset']], dataset=cell['dataset'])
    statepath = directory/'state.json'
    elapsed = load(statepath).get('active_seconds', 0) if statepath.exists() else 0
    start = time.monotonic()
    prior_stage = None
    total = probe_n if dev else cell['n']
    def status(kind, error=None):
        predictions = [load(p) for p in directory.glob('prediction_*.json')]
        progress = directory/'optimization.json'
        optimization = load(progress) if progress.exists() else {}
        value = dict(condition_id=cell['id'], dataset=cell['dataset'], method=cell['method'],
                     phase=cell['phase'], adaptation_gt=cell['adaptation_gt'], seed=cell['seed'],
                     status=kind, phase_active=prior_stage, attempted=len(predictions),
                     predicted=sum(p['valid'] for p in predictions),
                     adapted=optimization.get('evaluated_items', 0),
                     updated=optimization.get('full_development_evaluations', 0),
                     demos=optimization.get('demos'),
                     learned_context_tokens=optimization.get('learned_context_tokens'),
                     optimization_status=optimization.get('status'), total=total, judged=0,
                     judge_status='pending_selection', pid=os.getpid(),
                     active_seconds=elapsed+time.monotonic()-start, updated_at=time.time())
        if error: value['error_type'] = error
        atomic(statepath, value)
    try:
        status('running')
        # Optimization reads GT-bearing train and development records only, never test inputs.
        prior_stage = 'optimization'
        train = rows(parent/'data'/cell['dataset']/'train.jsonl')
        development = rows(parent/'data'/cell['dataset']/'dev.jsonl')
        if dev:
            def subset(records, tag):
                order, sources = probe_sources(native, records, probe_n, tag)
                return [sources[rid] for rid in order]
            train, development = subset(train, 'r7-train'), subset(development, 'r7-dev')
        program = compile_program(native, task, train, development, directory, cell['seed'], probe=dev)
        status('running')
        # The selected program is frozen before any evaluation input is read.
        prior_stage = 'evaluation'
        context = learned_context(program.classifier.signature, program.classifier.demos)
        frozen = dict(learned_context_sha256=hashlib.sha256(context.encode()).hexdigest(),
                      learned_context_tokens=len(native.tokenizer.encode(context)),
                      demos=len(program.classifier.demos))
        path = directory/'frozen_program.json'
        if path.exists():
            if load(path) != frozen: raise RuntimeError('Frozen program changed before evaluation')
        else: atomic(path, frozen)
        split = 'dev' if dev else 'test'
        data = rows(parent/'data'/cell['dataset']/(split+'.jsonl'))
        if dev: order, records = probe_sources(native, data, probe_n, 'r7-probe')
        else:
            order = load(stage/'orders.json')[cell['dataset']][str(cell['seed'])]['evaluation']
            records = {r['record_id']: r for r in data}
        for index, rid in enumerate(order):
            if (stage/'STOP').exists() or (parent/'STOP').exists(): raise KeyboardInterrupt()
            prediction_path = directory/f'prediction_{index:03d}.json'
            source = {'record_id': rid, 'text': records[rid]['text']}
            if prediction_path.exists():
                committed = load(prediction_path)
                if committed['record_id'] != rid: raise RuntimeError('Committed evaluation order changed')
                continue
            began = time.monotonic()
            messages = [dict(role='system', content=context),
                        dict(role='user', content=question(task, source)+FORMAT)]
            try:
                value, valid = generate_canonical(native, messages, task, f'evaluation:{index}:{rid}'), True
            except ValueError as exc:
                if str(exc) != 'Format retries exhausted': raise
                value, valid = None, False
            record = dict(record_id=rid, index=index, valid=valid, output=value, output_sha256=digest(value),
                          learned_context_sha256=frozen['learned_context_sha256'],
                          source_sha256=hashlib.sha256(source['text'].encode()).hexdigest(),
                          committed_at=time.time(), seconds=time.monotonic()-began)
            if valid:
                record.update(reported_offset_checks=evidence_checks(value, source['text']),
                              literal_anchors=literal_anchors(value, source['text']))
            else: record['error_type'] = 'exhausted_format_failure'
            atomic(prediction_path, record)
            status('running')
        predictions = [load(p) for p in directory.glob('prediction_*.json')]
        status('prediction_complete' if all(p['valid'] for p in predictions) else 'prediction_complete_with_failures')
    except BaseException as exc:
        status('paused' if isinstance(exc, KeyboardInterrupt) else 'failed', type(exc).__name__)
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--cell', required=True)
    parser.add_argument('--gpu', type=int, required=True)
    # The optimizer holds module-level runtime state and DSPy settings are process-global,
    # so every cell, development or production, runs in its own process.
    parser.add_argument('--dev', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    source = load(args.stage/'plan.json') if args.dev else verify(args.stage)
    cell = next(c for c in source['cells'] if c['id'] == args.cell)
    parent = Path(source['parent'])
    directory = args.stage/('preflight' if args.dev else 'runs')/cell['id']
    native = Native(directory/'calls', f'http://127.0.0.1:{11840+args.gpu}',
                    source['runtime']['tokenizer'], cell['seed'])
    execute(parent, args.stage, cell, native, dev=args.dev, probe_n=source['development_probe_n'])
