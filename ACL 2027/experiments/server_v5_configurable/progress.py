#!/usr/bin/env python3
"""Read-only terminal progress. Reads metadata only, never answers or source records."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DATASETS = {'dreaddit': 'Dreaddit', 'goemotions': 'GoEmotions', 'cache': 'CaChe', 'parlamint_gb': 'ParlaMint'}


def read_json(path, warnings):
    if not path.exists():
        return None
    try:
        with path.open() as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        warnings.append('{}: {}'.format(path.name, type(exc).__name__))
        return None


def process_alive(worker):
    if not worker or not worker.get('pid') or not worker.get('start_identity'):
        return None
    try:
        fields = Path('/proc/{}/stat'.format(worker['pid'])).read_text().split(') ', 1)[1].split()
        return fields[0] != 'Z' and fields[19] == str(worker['start_identity'])
    except (OSError, IndexError):
        return False


def read_stage(directory, manifest_name, queue_name, name, warnings):
    manifest = read_json(directory/manifest_name, warnings)
    if manifest is None:
        return None
    queue = read_json(directory/queue_name, warnings) or {}
    cells = manifest.get('cells', [])
    admitted = {c['id'] for c in manifest.get('admitted_cells', cells)}
    withheld = set(manifest.get('withheld_cells', []))
    active = {v: str(k) for k, v in queue.get('active', {}).items()}
    rows = []
    for cell in cells:
        run = directory/'runs'/cell['id']
        state = read_json(run/'state.json', warnings)
        exists = (run/'state.json').exists()
        state = state or {}
        worker = read_json(run/'worker.json', warnings) or {}
        raw_status = state.get('status', 'UNKNOWN' if exists else 'queued')
        is_held = cell['id'] in withheld or raw_status.startswith('withheld')
        alive = process_alive(worker)
        if is_held:
            status = 'HELD'
        elif raw_status == 'running':
            status = 'STOPPED' if alive is False else 'RUNNING'
        elif raw_status == 'prediction_complete':
            status = 'PRED DONE'
        elif raw_status == 'prediction_complete_with_failures':
            status = 'INVALID'
        else:
            status = raw_status.upper()
        rows.append(dict(cell=cell, state=state, worker=worker, status=status,
                         admitted=cell['id'] in admitted, stage=name,
                         gpu=active.get(cell['id'], str(worker.get('gpu', state.get('gpu', '-')))),
                         alive=alive))
    return dict(name=name, rows=rows, queue=queue, manifest=manifest,
                admitted=len(admitted), held=len(withheld),
                stamp=manifest.get('sealed_at', 0))


def snapshot(root, gpu=True):
    warnings = []
    stages = []
    base = read_stage(root, 'prediction_manifest.json', 'prediction_queue.json', 'Base/ICL', warnings)
    if base:
        stages.append(base)
    for path in sorted((root/'stages').glob('*')):
        if path.is_dir():
            stage = read_stage(path, 'manifest.json', 'queue.json', path.name, warnings)
            if stage:
                stages.append(stage)
    transition = read_json(root/'ACTIVE_ADAPTATION_STAGE.json', warnings) or {}
    development = []
    active_stage = transition.get('active_stage', '')
    if active_stage and '/' not in active_stage:
        for path in sorted((root/'stages'/active_stage/'preflight').glob('*/state.json')):
            state = read_json(path, warnings)
            if state:
                development.append({k: state.get(k) for k in ['condition_id', 'status', 'predicted', 'adapted', 'updated', 'total', 'updated_at']})
    gpu_rows = []
    if gpu:
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total',
                '--format=csv,noheader,nounits'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=3)
            if result.returncode:
                warnings.append('GPU telemetry unavailable')
            else:
                for line in result.stdout.splitlines():
                    parts = [x.strip() for x in line.split(',')]
                    if len(parts) == 4:
                        gpu_rows.append(parts)
        except (OSError, subprocess.TimeoutExpired):
            warnings.append('GPU telemetry unavailable')
    # Revisions may repeat conditions; never add these as independent experiment rows.
    selected = {}
    for stage in sorted(stages, key=lambda s: s['stamp']):
        for row in stage['rows']:
            c = row['cell']
            key = (c['dataset'], c['phase'], c['method'], c['adaptation_gt'], c['seed'])
            if row['admitted'] or key not in selected:
                selected[key] = row
    return dict(stages=stages, rows=list(selected.values()), warnings=warnings,
                gpus=gpu_rows, transition=transition, development=development, at=time.time(), monotonic=time.monotonic())


def amount(rows, field):
    return sum(r['state'].get(field, 0) for r in rows)


def fraction(done, total, width=20):
    proportion = done/total if total else 0
    filled = min(width, max(0, int(width*proportion)))
    return '[{}{}] {:5.1f}%'.format('#'*filled, '.'*(width-filled), 100*proportion)


def age(stamp, now):
    if not stamp:
        return '-'
    seconds = max(0, now-stamp)
    return '{}s'.format(int(seconds)) if seconds < 60 else '{}m'.format(int(seconds/60))


def display_row(row, now):
    c, s = row['cell'], row['state']
    phase = 'OFF' if c['phase'] == 'offline' else 'ON' if c['phase'] == 'online' else 'BASE'
    method = {'dc_cu': 'DC', 'ace': 'ACE', 'icl': 'ICL', 'base': 'Base'}.get(c['method'], c['method'])
    gt = {'yes': '+', 'no': '-', 'not_applicable': 'n/a'}.get(c['adaptation_gt'], '?')
    return '{:<10} {:<4} {:<6} {:>3} {:>2} {:>3} {:>5} {:>7} {:>5} {:>5} {:>5} {:<9}'.format(
        DATASETS.get(c['dataset'], c['dataset'])[:10], phase, method[:6], gt, c['seed'],
        row['gpu'] if row['status'] in ['RUNNING', 'STOPPED'] else '-',
        s.get('adapted', 0) if c['phase'] == 'offline' and c['method'] == 'ace' else '-',
        '{}/{}'.format(s.get('predicted', 0), s.get('attempted', 0)),
        s.get('updated', 0) if c['method'] in ['ace', 'dc_cu'] else '-',
        s.get('judged', 0), age(s.get('updated_at'), now), row['status'])


def render(value, previous=None, show_all=False, max_rows=15):
    rows, now = value['rows'], value['at']
    planned = max([s['manifest'].get('full_panel_runs', 84) for s in value['stages']] or [84])
    target = max([s['manifest'].get('full_panel_prediction_target',0) for s in value['stages']] or [0])
    valid, attempted, judged = [amount(rows, k) for k in ['predicted', 'attempted', 'judged']]
    running = [r for r in rows if r['status'] == 'RUNNING']
    failed = [r for r in rows if r['status'] in ['FAILED', 'STOPPED', 'UNKNOWN']]
    held = [r for r in rows if r['status'] == 'HELD']
    queued = [r for r in rows if r['status'] == 'QUEUED' and r['admitted']]
    invalid = [r for r in rows if r['status'] == 'INVALID']
    done = [r for r in rows if r['status'] == 'PRED DONE']
    unstarted = max(0, planned-len(rows))
    stamp = datetime.datetime.fromtimestamp(now).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    lines = ['ACL 2027 | Qwen3-8B | '+stamp,
        'Read-only live metadata | Evaluation sizes from the sealed sampling manifest | 4 corpora | seeds 42/43/44', '',
        'VALID predictions {:,}/{:,} {}  Attempts {:,}/{:,}'.format(valid, target, fraction(valid, target), attempted, target),
        'Judged {:,}/{:,} | Prediction-done {}/{} | Invalid-output runs {}'.format(judged, target, len(done), planned, len(invalid)),
        'Running {} | Queued {} | Failed/stopped {} | Held in preflight {} | Unstarted {}'.format(len(running), len(queued), len(failed), len(held), unstarted),
        'ETA: unavailable for the full panel while held/unstarted runs and judging remain.']
    transition = value.get('transition', {})
    if transition:
        lines.append('Execution: {} | {}'.format(transition.get('active_stage', '?'), transition.get('status', '?')))
        if transition.get('status') in ['waiting_for_predecessor_checkpoint', 'checkpoint_pause_for_format_revision']:
            lines.append('Format repair: old workers are draining at checkpoints; eight-GPU validation starts after the final request.')
        probes = value.get('development', [])
        if probes and transition.get('status') in ['preflight', 'pipeline_stopped', 'seal']:
            passed = sum(s['status']=='prediction_complete' and s['predicted']==6 and s['updated']==6 for s in probes)
            failed_dev = sum(s['status']=='failed' for s in probes)
            lines.append('Development validation: {}/18 passed | {} active | {} failed | {}/108 predictions | {}/108 updates'.format(
                passed, sum(s['status']=='running' for s in probes), failed_dev,
                sum(s.get('predicted',0) for s in probes), sum(s.get('updated',0) for s in probes)))
            lines.append('Development checks are separate from the evaluation totals above.')
    if previous and value['monotonic']-previous['monotonic'] >= 1:
        elapsed = value['monotonic']-previous['monotonic']
        old = {r['cell']['id']: r for r in previous['rows']}
        pred_delta = sum(max(0, r['state'].get('predicted', 0)-old[r['cell']['id']]['state'].get('predicted', 0)) for r in rows if r['cell']['id'] in old)
        update_delta = sum(max(0, r['state'].get('updated', 0)-old[r['cell']['id']]['state'].get('updated', 0)) for r in rows if r['cell']['id'] in old)
        lines.append('Last {:.0f}s: +{} predictions, +{} updates (short-window rates vary by phase)'.format(elapsed, pred_delta, update_delta))
    lines += ['', 'STAGES (revisions shown separately; full-panel totals select the latest admitted condition)']
    for stage in value['stages']:
        admitted = [r for r in stage['rows'] if r['admitted']]
        completed = sum(r['status'] == 'PRED DONE' for r in admitted)
        invalid_count = sum(r['status'] == 'INVALID' for r in admitted)
        stage_errors = sum(r['status'] in ['FAILED', 'STOPPED', 'UNKNOWN'] for r in admitted)
        lines.append('  {:<20} pred {:>4}/{:<4}  updates {:>4}  pred-done {:>2}/{:<2}'.format(
            stage['name'][:20], amount(admitted, 'predicted'), sum(r['cell']['n'] for r in admitted), amount(admitted, 'updated'),
            completed, len(admitted)))
        lines.append('    Invalid-output runs {} | Failed/stopped {} | Held {}'.format(invalid_count, stage_errors, stage['held']))
        changed = stage['queue'].get('updated_at')
        if stage['queue'].get('status') == 'running' and changed and now-changed > 90:
            lines.append('  WARNING: stage queue has not refreshed for '+age(changed, now))
    if not value['stages']:
        lines.append('  No supported execution manifest found at this root.')
    if value['gpus']:
        segments = ['{}: {}% {}/{}MiB'.format(*g) for g in value['gpus']]
        lines += ['', 'GPU utilization / allocated memory (server telemetry)']
        for i in range(0, len(segments), 4):
            lines.append('  '+' | '.join(segments[i:i+4]))
    lines += ['', 'RUNS (Train=adaptation attempts; Pred=valid/attempted; Upd=committed cycles)',
        'Dataset    Mode Method  GT Sd GPU Train    Pred   Upd Judge   Age Status',
        '-'*85]
    if show_all:
        displayed = rows
    else:
        failed.sort(key=lambda r: r['state'].get('updated_at', 0), reverse=True)
        displayed = running+failed
        if not displayed:
            displayed = (invalid+done+held+queued)[-max_rows:]
        displayed = displayed[:max_rows]
    for row in displayed:
        lines.append(display_row(row, now))
    if not show_all and len(rows) > len(displayed):
        lines.append('  Other rows hidden. Use --all to show every known condition; --once for one snapshot.')
    lines += ['', 'Updates include offline training cycles. PRED DONE is not fully judged.',
        'CaChe/ParlaMint accuracy: N/A. Source text, answers, labels and playbooks are never displayed.',
        'Refresh 5s by default | Ctrl+C exits this viewer; experiment workers continue.']
    if value['warnings']:
        lines.append('Metadata warnings: '+', '.join(sorted(set(value['warnings']))[:6]))
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--no-gpu', action='store_true')
    parser.add_argument('--no-clear', action='store_true')
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('Experiment root does not exist. Run this on the server or set --root.')
    if args.interval < 1:
        parser.error('--interval must be at least 1 second')
    interactive = sys.stdout.isatty() and not args.once and not args.no_clear
    previous = None
    try:
        if interactive:
            sys.stdout.write('\033[?1049h\033[?25l')
        while True:
            value = snapshot(args.root, gpu=not args.no_gpu)
            terminal_rows = shutil.get_terminal_size((100, 45)).lines
            output = render(value, previous, args.all, max_rows=max(8, terminal_rows-27))
            if interactive:
                sys.stdout.write('\033[H\033[2J')
            print(output, flush=True)
            if args.once:
                break
            previous = value
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if interactive:
            sys.stdout.write('\033[?25h\033[?1049l')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
