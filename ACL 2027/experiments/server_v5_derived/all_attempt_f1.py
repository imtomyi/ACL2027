"""Derived all-attempt classification F1 over committed predictions; never shrinks denominators.

An invalid output predicts no label: it adds a false negative for its reference label and no
false positive for any label. This matches accuracy, which counts invalid outputs as incorrect.
Sealed stage metrics are not modified. Values are published only after the derived formula
reproduces every stage F1 exactly on runs without invalid outputs.
"""
from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
from sklearn.metrics import precision_recall_fscore_support

PROTOCOL = 'classification-all-attempts-invalid-as-no-label-r1'


def load(path): return json.loads(Path(path).read_text())
def rows(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def all_attempt_f1(predictions, gold, task):
    labels = task['labels']
    if task['single_label']:
        # -1 lies outside the scored labels, so it is neither a true nor a false positive.
        y = np.array([gold[p['record_id']][0] for p in predictions])
        z = np.array([p['output']['label_ids'][0] if p['valid'] else -1 for p in predictions])
        scored = labels
    else:
        y = np.array([[int(k in gold[p['record_id']]) for k in labels] for p in predictions])
        z = np.array([[int(p['valid'] and k in p['output']['label_ids']) for k in labels] for p in predictions])
        scored = None
    values = {}
    for average in ['micro', 'macro']:
        _, _, f1, _ = precision_recall_fscore_support(y, z, average=average, labels=scored, zero_division=0)
        values[average+'_f1'] = 100*float(f1)
    return values


def derive(parent, output):
    tasks = load(parent/'tasks.json')
    sources = [(parent, 'prediction_manifest.json', 'live')]
    sources += [(d, 'manifest.json', d.name) for d in sorted((parent/'stages').glob('*')) if (d/'manifest.json').exists()]
    result, mismatches = [], []
    for directory, name, label in sources:
        manifest = load(directory/name)
        for cell in manifest.get('admitted_cells', manifest['cells']):
            if cell['dataset'] not in ['dreaddit', 'goemotions']: continue
            run = directory/'runs'/cell['id']
            predictions = [load(p) for p in sorted(run.glob('prediction_*.json'))]
            if len(predictions) != 100: continue
            gold = {r['record_id']: r['target'] for r in rows(parent/'data'/cell['dataset']/'test.jsonl')}
            if {p['record_id'] for p in predictions} != set(gold): raise RuntimeError('Evaluation IDs mismatch: '+cell['id'])
            invalid = sum(not p['valid'] for p in predictions)
            values = all_attempt_f1(predictions, gold, tasks[cell['dataset']])
            stage = load(run/'metrics.json') if (run/'metrics.json').exists() else {}
            match = None
            if invalid == 0 and stage.get('micro_f1') is not None:
                match = all(abs(stage[k]-values[k]) < 1e-9 for k in ['micro_f1', 'macro_f1'])
                if not match: mismatches.append(cell['id'])
            result.append(dict(cell=cell, stage=label, prediction_seal_sha256=manifest['seal_sha256'],
                               invalid_n=invalid, matches_stage_metric=match, **values))
    checked = sum(r['matches_stage_metric'] is not None for r in result)
    report = dict(protocol=PROTOCOL, status='validated' if checked and not mismatches else 'failed_validation',
                  rule=__doc__.strip().split('\n\n')[1].replace('\n', ' '),
                  validation=dict(runs_without_invalid_outputs_checked=checked, mismatches=mismatches),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  updated_at=time.time(), rows=result if not mismatches else [])
    output.mkdir(parents=True, exist_ok=True)
    (output/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], rows=len(result), checked=checked, mismatches=mismatches,
                          invalid_runs=[r['cell']['id'] for r in result if r['invalid_n']])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    derive(args.parent, args.output)
