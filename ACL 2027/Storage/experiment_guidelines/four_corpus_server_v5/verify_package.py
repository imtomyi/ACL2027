"""Read-only verification of this guideline package; no server or model calls."""
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    sources = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
    for item in sources['sources']:
        path = (ROOT / item['saved_as']).resolve()
        assert path.is_relative_to(ROOT), item['saved_as']
        assert path.is_file() and path.stat().st_size == item['bytes'], item['saved_as']
        assert sha(path) == item['sha256'], item['saved_as']
    old = ROOT / 'sources/previous_design/Storage/experiment_guidelines/four_corpus_server_v1'
    for name, digest in json.loads((old / 'design_hashes.json').read_text()).items():
        assert sha(old / name) == digest, name
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    with (ROOT / 'summary_template.csv').open() as f:
        summary = list(csv.DictReader(f))
    with (ROOT / 'metric_applicability.csv').open() as f:
        applicability = list(csv.DictReader(f))
    with (ROOT / 'metrics_long_template.csv').open() as f:
        fields = next(csv.reader(f))
    assert protocol['protocol_id'] == 'four-corpus-server-v5'
    conditions = protocol['conditions']
    assert len(conditions) == len(summary) == 28
    assert {x['condition_id'] for x in conditions} == {x['condition_id'] for x in summary}
    assert len({x['condition_id'] for x in conditions}) == 28
    assert sum(len(x['seeds']) for x in conditions) == 84
    assert all(x['eval_n'] == 100 and x['seeds'] == [42, 43, 44] for x in conditions)
    assert len(protocol['metrics']) == 85 and len(applicability) == 340
    assert len({x['metric_condition_id'] for x in applicability}) == 340
    matrix = {x['metric_condition_id']: x for x in applicability}
    for metric in protocol['metrics']:
        assert len(metric['dataset_conditions']) == 4
        for condition in metric['dataset_conditions']:
            assert matrix[condition['metric_condition_id']]['applicability'] == condition['applicability']
            if condition['dataset'] in ('cache', 'parlamint_gb') and metric['group'] in ('classification', 'joint', 'probabilistic'):
                assert condition['applicability'] == 'not_applicable'
    assert all(key in fields for key in protocol['required_metric_context_fields'])
    assert protocol['wall_clock_limit_seconds'] is None
    assert not protocol['historical_result_import_allowed']
    assert protocol['model'] is None and protocol['judge_model'] is None
    assert protocol['execution_manifest'] is None
    links = 0
    for path in ROOT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if not target.startswith(('http', '/', '#')):
                assert (path.parent / target.split('#')[0]).exists(), (path.name, target)
                links += 1
    package = ROOT / 'PACKAGE_HASHES.json'
    if package.exists():
        for name, digest in json.loads(package.read_text())['files'].items():
            path = (ROOT / name).resolve()
            assert path.is_relative_to(ROOT) and sha(path) == digest, name
    return dict(status='passed', protocol='four-corpus-server-v5',
                preserved_sources=len(sources['sources']), original_handoff_files=868,
                previous_design_hashes='passed', conditions=28, seed_runs=84,
                metric_entries=85, dataset_metric_entries=340, local_links=links,
                scope='Package integrity and design consistency, not execution readiness',
                network_calls=0, model_calls=0)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
