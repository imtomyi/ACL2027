#!/usr/bin/env python3
"""Additive development judging and read-only, matched evaluation comparisons."""
import argparse
import collections
import csv
import fcntl
import itertools
import json
from pathlib import Path

import run as core

METRICS = ('credibility', 'conformability', 'coverage')
HISTORICAL = core.WORKSPACE / 'Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2/quality/table3_export.csv'


def summarize(records):
    result = {'available_outputs': len(records)}
    for metric in METRICS:
        counts = collections.Counter()
        for row in records:
            status = row['status']
            if status == 'complete':
                value = row['judgments'][metric]['verdict']
                counts['T' if value is True else 'F' if value is False else 'U'] += 1
            else:
                counts['pending' if status == 'pending' else 'technical'] += 1
        t, f = counts['T'], counts['F']
        result[metric] = {key: counts[key] for key in ('T', 'F', 'U', 'technical', 'pending')}
        result[metric].update(binary_n=t+f, resolved_pct=round(100*t/(t+f), 2) if t+f else None)
    return result


def paired(left, right):
    shared = sorted(left.keys() & right.keys())
    result = {'shared_packets': len(shared), 'metrics': {}}
    for metric in METRICS:
        pairs = []
        for pid in shared:
            a, b = left[pid], right[pid]
            if a['status'] == b['status'] == 'complete':
                x, y = a['judgments'][metric]['verdict'], b['judgments'][metric]['verdict']
                if type(x) is bool and type(y) is bool:
                    pairs.append((x, y))
        n = len(pairs)
        result['metrics'][metric] = {
            'joint_binary_n': n, 'excluded_pending_unknown_or_technical': len(shared)-n,
            'left_only_pass': sum(a and not b for a, b in pairs),
            'right_only_pass': sum(b and not a for a, b in pairs),
            'ties': sum(a == b for a, b in pairs),
            'left_minus_right_pp': round(100*sum(int(a)-int(b) for a, b in pairs)/n, 2) if n else None,
        }
    return result


def setup(run):
    manifest = core.verify(run)
    folder = run / 'interim_quality'
    folder.mkdir(exist_ok=True, mode=0o700)
    contract_path = folder / 'manifest.json'
    bindings = {'parent_manifest_sha256': core.file_hash(run/'manifest.json'),
                'implementation_sha256': core.file_hash(__file__),
                'protocol_sha256': core.file_hash(Path(__file__).with_name('interim_quality.md'))}
    if contract_path.exists():
        contract = core.unseal(contract_path)
        if any(contract[k] != v for k, v in bindings.items()):
            raise core.ContractError('interim_contract_changed')
        if core.file_hash(folder/'historical_reference.csv') != contract['historical_sha256']:
            raise core.ContractError('historical_snapshot_changed')
    else:
        core.write(folder/'historical_reference.csv', HISTORICAL.read_text())
        core.seal(contract_path, {**bindings, 'created_at': core.now(),
            'historical_source': str(HISTORICAL), 'historical_sha256': core.file_hash(folder/'historical_reference.csv'),
            'historical_comparable': False, 'max_new_calls_per_tick': 1,
            'development_only_additional_judging': True, 'feedback_to_experiment': False,
            'manuscript_eligible': False})
    return folder, manifest


def dev_records(run, folder, manifest, infer):
    data, config = core.read(run/'inputs.private.json'), core.read(run/'config.json')
    config = {**config, 'transient_retries': 0}
    records, submitted = [], 0
    paths = sorted((run/'development').glob('*/*/*/result.json'), key=lambda p: (int(p.parent.name), str(p)))
    for source in paths:
        outcome = core.unseal(source)
        ds, model, pid = outcome['dataset'], outcome['model'], outcome['packet_id']
        packet = next(p for p in data[ds]['development'] if p['packet_id'] == pid)
        target = folder/'development'/ds/model.replace(':', '_')/pid
        path = target/'quality.json'
        meta = {'phase': 'development', 'dataset': ds, 'model': model, 'method': 'warrantroute',
                'packet_id': pid, 'episode': outcome['episode'], 'source_sha256': core.file_hash(source),
                'memory_before': outcome['memory_before'], 'task_sha256': core.digest(packet['task'])}
        if path.exists():
            row = core.unseal(path)
            if any(row[k] != v for k, v in meta.items()):
                raise core.ContractError('interim_source_changed')
            records.append(row)
            continue
        row = {**meta, 'status': 'pending'}
        if outcome['status'] != 'complete':
            row.update(status='technical_missing', error='development_incomplete', origin='generation_failure')
        else:
            artifact = {k: v for k, v in outcome['outcome']['artifact'].items() if k != 'used_bullet_ids'}
            payload = {'task': packet['task'], 'artifact': artifact}
            schema = core.schemas(packet['task'])[3]
            qualification = run/'qualification_quality'/ds/model.replace(':', '_')/'calls/qualification_judge.attempt0.json'
            if outcome['episode'] == 1 and qualification.exists():
                journal = core.unseal(qualification)
                expected = core.COMMON+'\n'+core.PROMPTS['judge']+'\n'+json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if (journal['request']['prompt'] != expected or journal['request']['format'] != schema
                        or journal['model'] != config['judge']):
                    raise core.ContractError('qualification_reuse_mismatch')
                row.update(origin='qualification_reuse', journal_sha256=core.file_hash(qualification))
                if journal['status'] == 'complete':
                    core.Draft202012Validator(schema).validate(journal['parsed'])
                    if core.integrity(journal['parsed'], packet['task']):
                        raise core.ContractError('qualification_evidence_invalid')
                    row.update(status='complete', judgments=journal['parsed'])
                elif journal['status'] != 'in_flight':
                    row.update(status='technical_missing', error=journal.get('error', 'qualification_incomplete'))
            elif outcome['episode'] != 1 and infer and submitted < 1:
                submitted += 1
                core.verify(run, service=True)
                client = core.Client(folder, target, config['judge'], config, manifest)
                row['origin'] = 'additional_development_judge'
                try:
                    judged = client.call('qualification_judge', 'judge', payload, schema)
                    if core.integrity(judged, packet['task']):
                        raise core.CallError('judge_evidence_quote_mismatch')
                    row.update(status='complete', judgments=judged)
                except core.CallError as exc:
                    row.update(status='technical_missing', error=str(exc))
                row['cost'] = core.cost(client.records)
        if row['status'] != 'pending':
            core.seal(path, {**row, 'recorded_at': core.now()})
        records.append(row)
    return records


def eval_records(run):
    records = []
    data = core.read(run/'inputs.private.json')
    tasks = {(ds, p['packet_id']): core.digest(p['task']) for ds, split in data.items() for p in split['evaluation']}
    for path in sorted((run/'evaluation').glob('*/*/*/*/result.json')):
        result = core.unseal(path)
        meta = {k: result[k] for k in ('dataset', 'model', 'method', 'packet_id')}
        quality = path.with_name('quality.json')
        row = core.unseal(quality) if quality.exists() else {'status': 'pending'}
        if quality.exists() and any(row[k] != v for k, v in meta.items()):
            raise core.ContractError('evaluation_quality_identity_mismatch')
        records.append({**row, **meta, 'phase': 'evaluation', 'task_sha256': tasks[(meta['dataset'], meta['packet_id'])]})
    return records


def comparisons(records):
    groups = collections.defaultdict(dict)
    for row in records:
        key = (row['phase'], row['dataset'], row['model'], row['method'])
        if row['packet_id'] in groups[key]:
            raise core.ContractError('duplicate_packet_in_cell')
        groups[key][row['packet_id']] = row
    contrasts = []
    for left, right in itertools.combinations(groups, 2):
        if left[:2] != right[:2]:
            continue
        same_model, same_method = left[2] == right[2], left[3] == right[3]
        if not (same_model ^ same_method):
            continue
        a, b = groups[left], groups[right]
        for pid in a.keys() & b.keys():
            if a[pid]['task_sha256'] != b[pid]['task_sha256']:
                raise core.ContractError('paired_input_changed')
        value = paired(a, b)
        if value['shared_packets']:
            contrasts.append({'phase': left[0], 'dataset': left[1], 'left': list(left[2:]),
                              'right': list(right[2:]), **value})
    rows = [{'phase': key[0], 'dataset': key[1], 'model': key[2], 'method': key[3],
             **summarize(list(value.values()))} for key, value in sorted(groups.items())]
    return rows, contrasts


def export(folder, records):
    rows, contrasts = comparisons(records)
    journals = [core.unseal(p) for p in (folder/'development').glob('**/calls/*.json')]
    historical = list(csv.DictReader((folder/'historical_reference.csv').open()))
    report = {'updated_at': core.now(), 'rows': rows, 'paired_comparisons': contrasts,
              'additional_judge_cost': core.cost(journals), 'historical_comparable': False,
              'historical_reason': 'Historical claim-review quality and current TA generation use different tasks and rubrics. No valid improvement delta.',
              'historical_reference': historical, 'development_is_exploratory': True,
              'manuscript_eligible': False}
    core.write(folder/'report.json', report)
    lines = ['# Interim quality monitoring', '',
        'Private exploratory diagnostics. Development quality is not held-out evaluation.',
        'Unknown, technical and pending cases are not counted as passes. Percentages use T/(T+F).',
        'A shared Qwen judge may favor its own model family; these are not independent human ratings.', '',
        '| Phase | Dataset | Model | Method | Outputs | Credibility T/N (%) | Conformability T/N (%) | Coverage T/N (%) |',
        '|---|---|---|---|---:|---:|---:|---:|']
    for row in rows:
        cells = []
        for metric in METRICS:
            x = row[metric]
            cells.append(f"{x['T']}/{x['binary_n']} ({x['resolved_pct'] if x['resolved_pct'] is not None else 'N/A'}); U={x['U']}, tech={x['technical']}, pending={x['pending']}")
        lines.append('| '+' | '.join(map(str, [row['phase'], row['dataset'], row['model'], row['method'], row['available_outputs'], *cells]))+' |')
    lines += ['', '## Matched comparisons', '',
        'Only identical packet IDs and evidence, same phase, same dataset and the fixed judge are compared.',
        'Deltas describe jointly binary cases only; missingness and small denominators limit interpretation.',
        'No significance claims, winner selection or automatic changes follow from these interim looks.', '']
    for contrast in contrasts:
        metrics = '; '.join(f"{m}: delta={contrast['metrics'][m]['left_minus_right_pp']} pp, n={contrast['metrics'][m]['joint_binary_n']}, excluded={contrast['metrics'][m]['excluded_pending_unknown_or_technical']}" for m in METRICS)
        lines.append(f"- {contrast['phase']} / {contrast['dataset']}: {' '.join(contrast['left'])} minus {' '.join(contrast['right'])}: {metrics}")
    if not any(c['phase'] == 'evaluation' for c in contrasts):
        lines.append('No matched held-out method/model comparisons yet. Do not infer which method is better.')
    lines += ['', '## Historical results', '', report['historical_reason'],
              'The unchanged historical values are in historical_reference.csv and report.json, for context only.',
              '', '## Execution', '',
              'The primary runner still judges each 50-output method batch. This sidecar adds at most one development judge call per scheduled tick.',
              'No sidecar judgments enter Playbook learning, official evaluation outputs, or the historical table.',
              f"Additional judge cost: {json.dumps(report['additional_judge_cost'])}"]
    core.write(folder/'report.md', '\n'.join(lines)+'\n')
    return {k: v for k, v in report.items() if k != 'historical_reference'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['tick', 'report'])
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_relative_to(core.OUTPUT_ROOT.resolve()):
        raise core.ContractError('invalid_parent_directory')
    folder, manifest = setup(run)
    with (folder/'worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'interim_already_running'}))
            return
        records = dev_records(run, folder, manifest, args.command == 'tick') + eval_records(run)
        result = export(folder, records)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
