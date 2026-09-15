"""Durable serial adaptation: commit the prediction before revealing current GT."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, sys, time
from core import atomic as original_atomic, load, rows, digest, evidence_checks
from retained_policy import Native
from predict_stage import literal_anchors
from adapters import ACE, DC, EMPTY, Upstream


def atomic(path, value):
    if path.parent.name == 'feedback_receipts' and path.exists():
        prior = load(path)
        assert {k: v for k, v in prior.items() if k != 'revealed_at'} == {k: v for k, v in value.items() if k != 'revealed_at'}
        assert prior['revealed_at'] >= prior['committed_at']
        return
    original_atomic(path, value)


def verify(stage):
    manifest = load(stage/'manifest.json')
    if manifest['seal_sha256'] != digest({k: v for k, v in manifest.items() if k != 'seal_sha256'}):
        raise RuntimeError('Adaptation manifest digest mismatch')
    for filename, checksum in manifest['files'].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != checksum:
            raise RuntimeError('Adaptation source seal changed: ' + filename)
    return manifest


def reference_for(parent, corpus, split, record_id):
    # Called only after a durable prediction. Only this item's target is returned.
    return next(r['target'] for r in rows(parent/'data'/corpus/(split+'.jsonl')) if r['record_id'] == record_id)


def execute(parent, stage, cell, native, upstream, dev=False, probe_n=6):
    directory = stage/('preflight' if dev else 'runs')/cell['id']
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory/'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    task = load(parent/'tasks.json')[cell['dataset']]
    algorithm = (ACE if cell['method'] == 'ace' else DC)(native, upstream, task)
    empty = EMPTY if cell['method'] == 'ace' else '(empty)'
    memory, next_id = empty, 1
    statepath = directory/'state.json'
    elapsed = load(statepath).get('active_seconds', 0) if statepath.exists() else 0
    start = time.monotonic()
    prior_stage = None
    def status(kind, error=None):
        predictions = [load(p) for p in directory.glob('prediction_*.json')]
        updates = list((directory/'updates').glob('*.json'))
        training = list(directory.glob('adaptation_prediction_*.json'))
        value = dict(condition_id=cell['id'], dataset=cell['dataset'], method=cell['method'],
                     phase=cell['phase'], adaptation_gt=cell['adaptation_gt'], seed=cell['seed'],
                     status=kind, phase_active=prior_stage, attempted=len(predictions),
                     predicted=sum(p['valid'] for p in predictions), adapted=len(training),
                     updated=len(updates), total=probe_n if dev else 100, judged=0,
                     judge_status='pending_selection', pid=os.getpid(),
                     active_seconds=elapsed+time.monotonic()-start, updated_at=time.time())
        if error: value['error_type'] = error
        atomic(statepath, value)
    try:
        status('running')
        phases = ['adaptation', 'evaluation'] if cell['phase'] == 'offline' else ['evaluation']
        for phase in phases:
            prior_stage = phase
            split = 'dev' if dev else 'train' if phase == 'adaptation' else 'test'
            data = rows(parent/'data'/cell['dataset']/(split+'.jsonl'))
            sources = {r['record_id']: {'record_id': r['record_id'], 'text': r['text']} for r in data}
            if dev:
                # Extreme lengths plus deterministic additional development sources, never test inputs.
                ordered = sorted(sources, key=lambda rid: (len(native.tokenizer.encode(sources[rid]['text'])), rid))
                order = [ordered[0], ordered[-1]]
                extra = sorted([rid for rid in ordered if rid not in order],
                    key=lambda rid: hashlib.sha256(('r2-probe:'+rid).encode()).hexdigest())
                order += extra[:max(0, probe_n-2)]
                if len(order) != probe_n: raise RuntimeError('Insufficient development probe sources')
            else:
                order = load(stage/'orders.json')[cell['dataset']][str(cell['seed'])][phase]
            updating = phase == 'adaptation' or cell['phase'] == 'online'
            for index, rid in enumerate(order):
                if (stage/'STOP').exists() or (parent/'STOP').exists(): raise KeyboardInterrupt()
                source = sources[rid]
                filename = ('adaptation_prediction_' if phase == 'adaptation' else 'prediction_')+f'{index:03d}.json'
                prediction_path = directory/filename
                update_path = directory/'updates'/f'{phase}_{index:03d}.json'
                memory_hash = digest(memory)
                began = time.monotonic()
                def commit(value, valid=True):
                    if prediction_path.exists(): raise RuntimeError('Prediction is already committed')
                    record = dict(record_id=rid, index=index, valid=valid, output=value,
                                  output_sha256=digest(value), memory_before_sha256=memory_hash,
                                  source_sha256=hashlib.sha256(source['text'].encode()).hexdigest(),
                                  committed_at=time.time(), seconds=time.monotonic()-began)
                    if valid:
                        record.update(reported_offset_checks=evidence_checks(value, source['text']),
                                      literal_anchors=literal_anchors(value, source['text']))
                    else: record['error_type'] = 'exhausted_format_failure'
                    atomic(prediction_path, record)
                    status('running')
                def reveal():
                    committed = load(prediction_path)
                    assert committed['valid'] and committed['memory_before_sha256'] == memory_hash
                    if cell['adaptation_gt'] == 'no': return None
                    if cell['dataset'] not in ['dreaddit', 'goemotions']: raise RuntimeError('Unavailable GT requested')
                    reference = reference_for(parent, cell['dataset'], split, rid)
                    atomic(directory/'feedback_receipts'/f'{phase}_{index:03d}.json',
                           dict(prediction_sha256=committed['output_sha256'],
                                committed_at=committed['committed_at'], revealed_at=time.time(),
                                reference_sha256=digest(reference), current_item_only=True))
                    return reference
                if prediction_path.exists():
                    prediction = load(prediction_path)
                    assert prediction['record_id'] == rid and prediction['memory_before_sha256'] == memory_hash
                    if not prediction['valid']:
                        if updating: raise ValueError('Prior failed adaptive prediction')
                        continue
                else: prediction = None
                if update_path.exists():
                    update = load(update_path)
                    assert prediction is not None and update['prediction_sha256'] == prediction['output_sha256']
                    assert update['memory_before_sha256'] == memory_hash
                    memory, next_id = update['memory'], update['next_id']
                    assert digest(memory) == update['memory_after_sha256']
                    continue
                key = f'{phase}:{index}:{rid}'
                try:
                    if cell['method'] == 'dc_cu':
                        if not updating: raise RuntimeError('DC is an online method in this panel')
                        update = algorithm.step(source, memory, next_id, key,
                            prediction['output'] if prediction else None, commit, reveal)
                    else:
                        if prediction is None:
                            commit(algorithm.generate(source, memory, key+':generate'))
                            prediction = load(prediction_path)
                        if updating:
                            update = algorithm.update(source, prediction['output'], memory, next_id,
                                index+1, len(order), reveal(), key)
                except ValueError as exc:
                    if str(exc) == 'Format retries exhausted' and not prediction_path.exists():
                        commit(None, False)
                        if not updating: continue
                    raise
                if updating:
                    prediction = load(prediction_path)
                    update.update(record_id=rid, index=index, prediction_sha256=prediction['output_sha256'],
                                  memory_before_sha256=memory_hash, memory_after_sha256=digest(update['memory']),
                                  completed_at=time.time(), seconds=time.monotonic()-began)
                    atomic(update_path, update)
                    memory, next_id = update['memory'], update['next_id']
                status('running')
            if phase == 'adaptation':
                frozen = dict(memory=memory, next_id=next_id, memory_sha256=digest(memory), updates=len(order))
                path = directory/'frozen_playbook.json'
                if path.exists(): assert load(path) == frozen
                else: atomic(path, frozen)
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
    args = parser.parse_args()
    os.umask(0o077)
    manifest = verify(args.stage)
    cell = next(c for c in manifest['cells'] if c['id'] == args.cell)
    parent = Path(manifest['parent'])
    native = Native(args.stage/'runs'/cell['id']/'calls', f'http://127.0.0.1:{11840+args.gpu}',
                    manifest['runtime']['tokenizer'], cell['seed'])
    execute(parent, args.stage, cell, native, Upstream(args.stage/'upstream'))
