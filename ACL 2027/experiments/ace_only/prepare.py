#!/usr/bin/env python3
"""Verify frozen ACE-only inputs; optionally download/rebuild missing public data.

No model calls, experimental outputs, or changes to existing input files.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import ssl
import sys
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url, target, expected):
    if target.exists():
        if digest(target) != expected:
            raise ValueError(f'Existing input differs; preserved: {target.relative_to(ROOT)}')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'ACL2027-ACE-replication'})
        # Python.org macOS installations may not have a populated default CA store.
        # The reference environment pins certifi; keep TLS verification enabled.
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=120, context=context) as response, temp.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        if digest(temp) != expected:
            raise ValueError(f'Download hash mismatch: {target.relative_to(ROOT)}')
        # Exclusive creation avoids replacing an input created by another worker.
        with target.open('xb') as stream, temp.open('rb') as source:
            shutil.copyfileobj(source, stream)
    finally:
        temp.unlink(missing_ok=True)


def rebuild_dreaddit(manifest):
    target = ROOT / 'dataset/deidentified/dreaddit/records.jsonl'
    if target.exists():
        return
    archive_spec = manifest['dreaddit_archive']
    raw = ROOT / 'dataset/raw/dreaddit'
    archive = raw / 'dreaddit.zip'
    fetch(archive_spec['url'], archive, archive_spec['sha256'])
    with zipfile.ZipFile(archive) as source:
        for spec in archive_spec['raw_files']:
            dest = raw / spec['name']
            matches = [n for n in source.namelist() if Path(n).name == spec['name']]
            if len(matches) != 1:
                raise ValueError('Ambiguous author archive member')
            data = source.read(matches[0])
            if hashlib.sha256(data).hexdigest() != spec['sha256']:
                raise ValueError('Author CSV hash mismatch')
            if not dest.exists():
                with dest.open('xb') as stream:
                    stream.write(data)
            elif digest(dest) != spec['sha256']:
                raise ValueError('Existing author CSV differs; preserved')
    script = ROOT / 'dataset/scripts/prepare_corpora.py'
    if digest(script) != manifest['files'][str(script.relative_to(ROOT))]['sha256']:
        raise ValueError('Dreaddit processing code differs from the frozen version')
    spec = importlib.util.spec_from_file_location('ace_dreaddit_preparation', script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        module.prepare_dreaddit(raw, Path(temporary))
        prepared = Path(temporary) / 'dreaddit/records.jsonl'
        expected = manifest['files'][str(target.relative_to(ROOT))]['sha256']
        if digest(prepared) != expected:
            raise ValueError('Rebuilt Dreaddit does not match reference bytes')
        with target.open('xb') as stream, prepared.open('rb') as source:
            shutil.copyfileobj(source, stream)


def load_selected():
    """Return real rows after verifying the manifest; never print their text."""
    package = json.loads((HERE / 'package_manifest.json').read_text())
    for relative, expected in package['files_sha256'].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'Package file missing or modified: {relative}')
    manifest = json.loads((HERE / 'data_sources.json').read_text())
    for relative, spec in manifest['files'].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != spec['sha256']:
            raise ValueError(f'Missing or mismatched input: {relative}')
    frozen = json.loads((HERE / 'selection.json').read_text())['datasets']
    source = ROOT / 'dataset/deidentified/dreaddit/records.jsonl'
    dread = {r['record_id']: r for r in map(json.loads, source.read_text().splitlines())}
    split_ids = json.loads((ROOT / 'Storage/dreaddit_icl/comparison_preparation_20260912/splits.json').read_text())['ids']
    pools = {'dreaddit': {name: [dict(record_id=i, text=dread[i]['text'], target=[int(dread[i]['sampling_strata']['stress_label'])])
                               for i in split_ids[original]] for name, original in [('adapt', 'train'), ('test', 'test')]}}
    pools['goemotions'] = {}
    for name, original in [('adapt', 'train'), ('test', 'test')]:
        path = ROOT / f'dataset/raw/goemotions/upstream/{original}.tsv'
        with path.open() as stream:
            pools['goemotions'][name] = [dict(record_id=r[2], text=r[0], target=sorted(map(int, r[1].split(',')))) for r in csv.reader(stream, delimiter='\t')]
    for corpus in ('cache', 'parlamint_gb'):
        pools[corpus] = {}
        for name in ('adapt', 'test'):
            path = ROOT / f'Storage/paired_feedback/run_20260912/data/{corpus}_{name}.jsonl'
            pools[corpus][name] = list(map(json.loads, path.read_text().splitlines()))
    result = {}
    for corpus, sets in frozen.items():
        result[corpus] = {}
        for split, spec in sets.items():
            ranked = sorted(pools[corpus][split], key=lambda r: hashlib.sha256(f"budget-pilot-v1:42:{spec['key_split']}:{r['record_id']}".encode()).hexdigest())[:spec['n']]
            assert [r['record_id'] for r in ranked] == spec['record_ids'], (corpus, split, 'IDs')
            assert [hashlib.sha256(r['text'].encode()).hexdigest() for r in ranked] == spec['text_sha256'], (corpus, split, 'text hashes')
            assert len({r['record_id'] for r in ranked}) == spec['n']
            result[corpus][split] = ranked
        assert not ({r['record_id'] for r in result[corpus]['adapt']} & {r['record_id'] for r in result[corpus]['test']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-missing', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    manifest = json.loads((HERE / 'data_sources.json').read_text())
    if args.download_missing:
        for relative, spec in manifest['files'].items():
            if spec.get('download_url'):
                fetch(spec['download_url'], ROOT / relative, spec['sha256'])
        rebuild_dreaddit(manifest)
    selected = load_selected()
    print(json.dumps({'status': 'verified', 'project_root': str(ROOT), 'counts': {c: {s: len(rows) for s, rows in sets.items()} for c, sets in selected.items()}, 'inference_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
