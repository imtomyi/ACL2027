"""Declared r4 recovery: unchanged requests, bounded retries, preserved checkpoints."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, subprocess, sys, time

ROOT = Path('/home/sy23985/Storage/acl2027_server_v5_20260914')
PY = '/home/sy23985/Storage/acl2027_miata_resume_20260913/runtime/venv/bin/python'
CELLS = [('cache__online__dc_cu__gt_no__seed44', 7),
         ('goemotions__online__dc_cu__gt_yes__seed44', 1)]
REVISION = 'dc-r4-unicode-transport-recovery-v1'


def load(path):
    return json.loads(path.read_text())


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return fields[19] if fields[0] != 'Z' else None
    except FileNotFoundError:
        return None


def unicode_scalar_strings(value):
    """Reject invalid strings; never replace, drop, or normalize a character."""
    if isinstance(value, str):
        value.encode('utf-8', errors='strict')
    elif isinstance(value, dict):
        for key, item in value.items():
            unicode_scalar_strings(key)
            unicode_scalar_strings(item)
    elif isinstance(value, list):
        for item in value:
            unicode_scalar_strings(item)


def recovery_native(base):
    class RecoveryNative(base):
        def structured(self, messages, role, key, schema, validator):
            if role == 'curator' and 'memory_items' in schema.get('properties', {}):
                original_validator = validator
                def checked(value):
                    original_validator(value)
                    unicode_scalar_strings(value)
                validator = checked
            return super().structured(messages, role, key, schema, validator)

        def chat(self, *args, **kwargs):
            # The original core consumes distinct preserved attempt receipts and
            # caps each exact request at three. Only incomplete responses retry.
            for attempt in range(3):
                try:
                    return super().chat(*args, **kwargs)
                except RuntimeError as exc:
                    if str(exc) != 'Incomplete inference response' or attempt == 2:
                        raise
                    time.sleep(2)
    return RecoveryNative


def preserve_feedback(original):
    def write(path, value):
        if path.parent.name == 'feedback_receipts' and path.exists():
            prior = load(path)
            assert {k: v for k, v in prior.items() if k != 'revealed_at'} == {
                k: v for k, v in value.items() if k != 'revealed_at'}
            assert prior['revealed_at'] >= prior['committed_at']
            return
        original(path, value)
    return write


def prefix_hashes(directory):
    paths = list(directory.glob('prediction_*.json'))
    for name in ['updates', 'feedback_receipts', 'calls']:
        paths.extend((directory / name).glob('*.json'))
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def worker(control, cell_id, gpu):
    stage = ROOT / 'stages/adaptation_r4'
    sys.path[:0] = [str(stage / 'code'), str(ROOT / 'code')]
    import run
    from core import Native
    from adapters import Upstream
    manifest = run.verify(stage)
    cell = next(c for c in manifest['admitted_cells'] if c['id'] == cell_id)
    directory = stage / 'runs' / cell_id
    before = load(control / cell_id / 'prefix.json')
    assert all(hashlib.sha256((directory / p).read_bytes()).hexdigest() == sha
               for p, sha in before.items())
    run.atomic = preserve_feedback(run.atomic)
    native = recovery_native(Native)(directory / 'calls', f'http://127.0.0.1:{11840+gpu}',
                                     manifest['runtime']['tokenizer'], cell['seed'])
    try:
        run.execute(ROOT, stage, cell, native, Upstream(stage / 'upstream'))
    finally:
        changed = [p for p, sha in before.items()
                   if not (directory / p).exists()
                   or hashlib.sha256((directory / p).read_bytes()).hexdigest() != sha]
        atomic(control / cell_id / 'PREFIX_AUDIT.json',
               dict(checked=len(before), changed=changed, passed=not changed, at=time.time()))
        if changed:
            raise RuntimeError('Recovery changed preserved evidence')


def controller(control):
    stage = ROOT / 'stages/adaptation_r4'
    locks = []
    for path in [ROOT / 'prediction_controller.lock', stage / 'controller.lock']:
        lock = path.open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(lock)
    assert not (ROOT / 'STOP').exists() and not (stage / 'STOP').exists()
    manifest = load(control / 'MANIFEST.json')
    assert manifest['revision'] == REVISION
    assert manifest['source_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert load(control / 'VALIDATION.json')['passed']
    assert load(ROOT / 'joint_adaptation/queue.json')['status'] == 'complete'
    for path in ROOT.glob('stages/*/runs/*/worker.json'):
        previous = load(path)
        assert identity(previous['pid']) != previous['start_identity'], 'Previous worker still active'
    atomic(control / 'dispatch.json', dict(pid=os.getpid(), start_identity=identity(os.getpid()),
                                         started_at=time.time(), revision=REVISION))
    owned = {s['gpu']: s for s in load(ROOT / 'services/ownership.json')['services']}
    listing = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
                                      '--format=csv,noheader,nounits'], text=True)
    for cell, gpu in CELLS:
        service = owned[gpu]
        assert identity(service['pid']) == service['start_identity']
        for line in listing.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) == 2 and parts[0] == service['uuid']:
                try:
                    env = Path(f'/proc/{int(parts[1])}/environ').read_bytes().split(b'\0')
                except FileNotFoundError:
                    continue
                assert f'OLLAMA_HOST=127.0.0.1:{11840+gpu}'.encode() in env, 'Foreign GPU use'
    active, finished = {}, {}
    for cell, gpu in CELLS:
        directory = stage / 'runs' / cell
        state = load(directory / 'state.json')
        if state['status'] == 'prediction_complete':
            finished[cell] = state['status']
            continue
        assert state['status'] == 'failed', 'Unexpected state; inspect before resuming'
        saved = control / cell
        assert not (saved / 'prefix.json').exists(), 'Recovery already prepared'
        atomic(saved / 'prefix.json', prefix_hashes(directory))
        for name in ['state.json', 'worker.json']:
            atomic(saved / ('before_' + name), load(directory / name))
        with (saved / 'worker.log').open('ab') as log:
            p = subprocess.Popen([PY, str(Path(__file__)), '--control', str(control),
                '--cell', cell, '--gpu', str(gpu)], stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, start_new_session=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', HF_HUB_OFFLINE='1',
                         TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false'))
        atomic(directory / 'worker.json', dict(pid=p.pid, start_identity=identity(p.pid),
               gpu=gpu, started_at=time.time(), controller=str(control), revision=REVISION))
        active[gpu] = (p, cell)
    while True:
        for gpu, (p, cell) in list(active.items()):
            if p.poll() is not None:
                finished[cell] = load(stage / 'runs' / cell / 'state.json')['status']
                del active[gpu]
        status = 'running' if active else 'complete' if all(
            s == 'prediction_complete' for s in finished.values()) else 'needs_attention'
        atomic(control / 'queue.json', dict(status=status, active={str(g): c for g, (_, c) in active.items()},
               finished=finished, queued=0, updated_at=time.time(), revision=REVISION))
        atomic(ROOT / 'ACTIVE_ADAPTATION_STAGE.json', dict(active_stage='adaptation_r4',
               continuing_ace_stage='adaptation_r3', status='dc_recovery_' + status,
               recovery_revision=REVISION, recovery_controller=str(control), at=time.time()))
        env = dict(os.environ, PYTHONPATH=str(stage / 'code') + os.pathsep + str(ROOT / 'code'),
                   PYTHONDONTWRITEBYTECODE='1')
        with (control / 'reports.log').open('ab') as log:
            subprocess.run([PY, str(stage / 'code/stage.py'), 'report', '--stage', str(stage)],
                           env=env, stdout=log, stderr=log, check=True)
        if not active:
            break
        time.sleep(15)


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--cell')
    parser.add_argument('--gpu', type=int)
    args = parser.parse_args()
    worker(args.control, args.cell, args.gpu) if args.cell else controller(args.control)
