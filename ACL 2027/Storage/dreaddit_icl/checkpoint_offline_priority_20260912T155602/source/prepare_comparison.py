"""Prepare text-free splits, source snapshots, protocol, and cost scenarios. No inference."""
import ast
import hashlib
import json
import os
from pathlib import Path
import random
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Storage/dreaddit_icl/comparison_preparation_20260912'


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Dreaddit-reproduction-preparation'})
    return urllib.request.urlopen(request, timeout=60).read()


def main():
    os.umask(0o077)
    OUT.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'dataset/deidentified/dreaddit/records.jsonl'
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    quarantine = json.loads((ROOT / 'dataset/audits/dreaddit_exact_date_quarantine.json').read_text())
    excluded = {r['source_id'] for r in quarantine['matches']}
    eligible = [r for r in rows if r['quality']['eligible_for_packet_sampling']
                and r['source_id'] not in excluded]
    development = [r for r in eligible if r['split'] == 'development_train']
    test = [r for r in eligible if r['split'] == 'in_domain_audit']
    groups = sorted({r['source_id'] for r in development})
    random.Random(42).shuffle(groups)
    validation_groups = set(groups[:round(len(groups) * .2)])
    train = [r for r in development if r['source_id'] not in validation_groups]
    validation = [r for r in development if r['source_id'] in validation_groups]
    random.Random(42).shuffle(train)
    random.Random(42).shuffle(test)
    assert not {r['source_id'] for r in train} & {r['source_id'] for r in validation}
    assert not {r['source_id'] for r in development} & {r['source_id'] for r in test}
    splits = {k: [r['record_id'] for r in v] for k, v in
              [('train', train), ('validation', validation), ('test', test)]}
    write('splits.json', dict(ids=splits, counts={k: len(v) for k, v in splits.items()},
                             seed=42, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                             note='All eligible records retained; 20% development post groups held out for validation.'))
    snapshots = OUT / 'source_snapshots'
    snapshots.mkdir()
    sources = []
    for repo, ref, files in [
        ('stanfordnlp/dspy', '3.0.3', ['dspy/teleprompt/mipro_optimizer_v2.py', 'dspy/teleprompt/gepa/gepa.py']),
        ('suzgunmirac/dynamic-cheatsheet', 'main', ['README.md', 'prompts/curator_prompt_for_dc_cumulative.txt']),
    ]:
        commit = json.loads(get(f'https://api.github.com/repos/{repo}/commits/{ref}'))['sha']
        for filename in files:
            url = f'https://raw.githubusercontent.com/{repo}/{commit}/{filename}'
            content = get(url)
            local = repo.replace('/', '_') + '_' + filename.replace('/', '_')
            (snapshots / local).write_bytes(content)
            sources.append(dict(repo=repo, ref=ref, commit=commit, path=filename, url=url,
                                sha256=hashlib.sha256(content).hexdigest(), snapshot=local))
    sources.append(dict(repo='ace-agent/ace', commit='82709de050e1db6e6ef2f07bcb0393560b94992a',
                        local_path=str(ROOT.parent / 'ace_paper/original_sources/ace'),
                        note='Existing pinned official checkout; do not edit.'))
    write('sources.json', dict(sources=sources,
          caveat='DSPy 3.0.3 is an explicit implementation baseline, not a verified paper environment. DC snapshot is current; historical paper commit is unknown.'))
    # Extract the published budget function, without importing or running an optimizer.
    gepa_path = next(snapshots / s['snapshot'] for s in sources if s.get('path', '').endswith('gepa/gepa.py'))
    tree = ast.parse(gepa_path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'GEPA')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'auto_budget')
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<budget-only>', 'exec'), namespace)
    budget = namespace['auto_budget'](None, 1, 18, len(validation))
    matrix = [dict(method='base', mode='none', gt=None), dict(method='icl', mode='offline', gt=True),
              dict(method='miprov2', mode='offline', gt=True, auto='heavy'),
              dict(method='gepa', mode='offline', gt=True, auto='heavy', metric_budget=budget)]
    for method, modes in [('dc_cu', ['online']), ('ace', ['offline', 'online'])]:
        for mode in modes:
            for gt in [True, False]:
                matrix.append(dict(method=method, mode=mode, gt=gt))
    assert len(matrix) == 10
    write('protocol.json', dict(status='prepared_specification_not_implemented_or_executed', matrix=matrix,
          model='qwen3:8b', quantization='Q4_K_M', thinking=False, parallelism=1,
          context_tokens=32768, output_cap_per_call=4096, seed=42,
          ace=dict(epochs=5, reflection_rounds=5, curator_frequency=1, validation_frequency=100,
                   online_window=1, initial_playbook='empty', deduplication_threshold=.9,
                   playbook_soft_cap_tokens=16000, overflow='fail_before_truncation'),
          gt_no_policy='strict: no labels, correctness feedback, label-dependent branching, or label-based checkpoint selection',
          gt_no_validation='none; use final checkpoint',
          strict_no_gt_reflection='fixed one reflection then curator; do not use hidden correctness to select rounds',
          outputs=['accuracy', 'macro_f1', 'invalid_rate', 'tokens_by_role', 'wall_time_by_phase', 'prequential_scores'],
          paper_deviations=['model and dataset', 'quantization', 'context and playbook cap',
                            'development split', 'strict GT-no control flow', 'online window 1 versus released default 100',
                            'software version provenance not fully specified by paper']))
    scenarios = {
        'fast_assumption': dict(prediction=2, icl_prediction=3, cold_prefix=120, ace_step=45, dc_step=30, search_reflection=30),
        'middle_assumption': dict(prediction=8, icl_prediction=12, cold_prefix=300, ace_step=120, dc_step=90, search_reflection=90),
        'slow_assumption': dict(prediction=20, icl_prediction=40, cold_prefix=900, ace_step=300, dc_step=240, search_reflection=240),
    }
    estimates = {}
    for epochs in [1, 5]:
        estimates[str(epochs)] = {}
        for name, s in scenarios.items():
            n, v, t = len(train), len(validation), len(test)
            # MIPRO uses 27 trials for a single predictor in this pinned version.
            # Seven full validation sweeps + 27 minibatches + 90 bootstrap calls is a planning allowance.
            search_calls = 7 * v + 27 * 35 + 90
            hours = dict(base=t*s['prediction']/3600,
                         icl=(s['cold_prefix']+t*s['icl_prediction'])/3600,
                         miprov2=((search_calls+t)*s['prediction']+18*s['search_reflection'])/3600,
                         gepa=((budget+t)*s['prediction']+180*s['search_reflection'])/3600)
            for gt in ['yes', 'no']:
                hours['dc_online_gt_'+gt] = t*s['dc_step']/3600
                hours['ace_online_gt_'+gt] = t*(s['ace_step']+s['prediction'])/3600
                val_calls = epochs*(n//100)*v if gt=='yes' else 0
                hours['ace_offline_gt_'+gt] = (epochs*n*s['ace_step']+(val_calls+t)*s['prediction'])/3600
            estimates[str(epochs)][name] = dict(hours=hours, total_hours=sum(hours.values()),
                                               total_days=sum(hours.values())/24)
    write('time_estimates.json', dict(measured=False, assumptions_seconds=scenarios,
          counts={k:len(v) for k,v in splits.items()}, gepa_metric_budget=budget,
          caveats=['Not hardware benchmarks or confidence intervals.',
                   'ACE step includes 4-13 main LLM calls for released GT-yes flow; strict GT-no differs.',
                   'Analyzer work, growing prompts, retries and thermal effects must fit step-time assumptions or add time.',
                   'GEPA reflection count 180 is a scenario allowance, not a source-derived cap.',
                   'MIPRO calls are an allowance; DSPy cache can reduce actual model calls.',
                   'No checkpoint validation in strict GT-no; GT-yes uses every 100 steps.',
                   'Offline final epoch and online final updates may incur unnecessary but accounted diagnostics.'],
          estimates=estimates))
    print(json.dumps(dict(output=str(OUT), counts={k:len(v) for k,v in splits.items()},
                         gepa_metric_budget=budget, totals={e:{k:round(v['total_days'],1) for k,v in d.items()} for e,d in estimates.items()})))


if __name__ == '__main__':
    main()
