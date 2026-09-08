#!/usr/bin/env python3
"""Build an offline, restricted catalog from existing experiment evidence only."""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BANKS = ROOT / 'Storage/draft_review_packets'
SCRIPTS = ROOT / 'experiments/rq2_role_prompted_llm/scripts'
CONFIG = ROOT / 'experiments/rq2_role_prompted_llm/config/table3_n100_prompt_identity_repair_v1.json'
QUALITY = BANKS / 'table3_review_quality_v1/runs/review_quality_n100_20260904_r2/units.jsonl'
ORDER = ['dreaddit', 'goemotions', 'agyw_focus_groups', 'parlamint_gb']
NAMES = dict(zip(ORDER, ['Dreaddit', 'GoEmotions', 'CaChe', 'ParlaMint-GB']))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    with path.open(encoding='utf-8') as stream:
        for line, text in enumerate(stream, 1):
            if text.strip():
                yield line, json.loads(text)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(text, encoding='utf-8')
    path.chmod(0o600)


def write_json(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def pipeline_evidence():
    run = ROOT / 'Storage/rq2_personal_local_diagnostic/warrantroute_live_loop/n100_same_model_table3_20260905_v2'
    manifest = read_json(run / 'manifest.json')
    quality = read_json(run / 'quality/manifest.json')
    files = []

    def add(path, stage, expected=None):
        raw = path.read_bytes()
        actual = digest(raw)
        if expected is not None and actual != expected:
            raise ValueError(f'Catalog evidence hash mismatch: {path}')
        files.append({**link(path), 'name': path.name, 'stage': stage,
                      'sha256': actual, 'frozen': expected is not None,
                      'text': raw.decode('utf-8')})

    for name in ['build_working_dreaddit_packet_bank.py', 'build_working_multicorpus_packet_banks.py',
                 'build_parlamint_full_sample_bank.py', 'run_all_usable_table3_queue.py']:
        add(SCRIPTS / name, '1. Construct packets and select n100 (source references)')
    for relative, expected in manifest['assets'].items():
        add(run / relative, '2. Execute WarrantRoute and score detection (frozen)', expected)
    for binding in quality['bindings']:
        path = Path(binding['path'])
        if path.is_relative_to(run / 'quality') and (
                'implementation' in path.parts or path.name in ['prompt.txt', 'schema.json', 'protocol.md', 'design.json']):
            add(path, '3. Judge review quality and export Table 3 (frozen)', binding['sha256'])
    return {'run_id': run.name, 'files': files,
            'manifest': link(run / 'manifest.json'), 'quality_manifest': link(run / 'quality/manifest.json')}


def render_viewer(data):
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (HERE / 'viewer.template.html').read_text(encoding='utf-8')
    assert template.count('__CATALOG_DATA__') == 1
    evidence = json.dumps(pipeline_evidence(), ensure_ascii=True).replace('<', '\\u003c')
    assert template.count('__PIPELINE_DATA__') == 1
    write(HERE / 'index.html', template.replace('__CATALOG_DATA__', payload).replace('__PIPELINE_DATA__', evidence))


def link(path):
    return {'path': str(path.resolve()), 'url': path.resolve().as_uri()}


def csv_export(name, records):
    path = HERE / name
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        for record in records:
            # Spreadsheet formula escaping is display-only. JSON preserves exact text.
            writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v
                             for k, v in record.items()})
    path.chmod(0o600)


def source_index(packets):
    needed = {(p['corpus_id'], e['source_record_id']) for p in packets for e in p['packet']['source_text_context']}
    result = {}
    agyw = read_json(ROOT / 'dataset/manifests/agyw_source_manifest.json')
    fgd_names = {f['doc_id']: f['name'] for f in agyw['files']}
    for corpus in ['dreaddit', 'agyw_focus_groups']:
        path = ROOT / f'dataset/deidentified/{corpus}/records.jsonl'
        for line, record in rows(path):
            key = (corpus, record['record_id'])
            if key not in needed:
                continue
            prov = record['provenance']
            if corpus == 'dreaddit':
                raw = ROOT / f"dataset/raw/dreaddit/dreaddit-{prov['source_file_role']}.csv"
                location = f"CSV data row {prov['source_row']} (header excluded); sentence_range={record['context']['sentence_range']}"
            else:
                raw = ROOT / 'dataset/raw/agyw_focus_groups' / fgd_names[record['source_id']]
                location = f"Transcript lines {prov['source_line_start']}-{prov['source_line_end']}; turn {prov['source_turn_index']}"
            assert raw.is_file(), raw
            result[key] = {'text': record['text'], 'analysis_file': link(path), 'analysis_line': line,
                           'raw_file': link(raw), 'raw_location': location, 'provenance': prov,
                           'preparation': record['quality'], 'source_context_record': record['context'],
                           'verification_basis': 'Exact comparison with the stored deidentified analysis record; raw location from its provenance.'}
    path = ROOT / 'dataset/raw/goemotions/upstream/train.tsv'
    for line, text in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        key = ('goemotions', f'goemotions_train_{line:05d}')
        if key not in needed:
            continue
        content, labels, comment_id = text.split('\t')
        result[key] = {'text': re.sub(r'\s+', ' ', content).strip(), 'analysis_file': link(path),
                       'analysis_line': line, 'raw_file': link(path), 'raw_location': f'TSV row {line} (no header)',
                       'provenance': {'source_row': line, 'original_emotion_label_ids': labels.split(','),
                                      'comment_id_sha256': digest(comment_id.encode())},
                       'verification_basis': 'Exact comparison after the original builder whitespace normalization.'}
    # Match only the required parliamentary sessions without extracting the archive.
    targets = defaultdict(list)
    for p in packets:
        if p['corpus_id'] == 'parlamint_gb':
            for e in p['packet']['source_text_context']:
                targets[e['source_id']].append(e)
    archive = ROOT / 'dataset/raw/parlamint_gb/ParlaMint-GB.tgz'
    sys.path.insert(0, str(SCRIPTS))
    from build_parlamint_full_sample_bank import elem_text
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith('.xml') or Path(member.name).stem not in targets:
                continue
            tree = ET.parse(tar.extractfile(member)).getroot()
            wanted = targets[Path(member.name).stem]
            turns = [e for e in tree.iter() if e.tag.split('}')[-1] == 'u']
            for excerpt in wanted:
                key = ('parlamint_gb', excerpt['source_record_id'])
                if key in result:
                    continue
                matches = [(n, e) for n, e in enumerate(turns, 1)
                           if e.attrib.get('who') == excerpt['speaker_id'] and elem_text(e) == excerpt['text']]
                result[key] = {'text': excerpt['text'] if matches else None,
                               'raw_file': link(archive), 'raw_location': member.name,
                               'provenance': {'archive_member': member.name, 'match_count': len(matches),
                                              'matches': [{'xml_id': e.attrib.get('{http://www.w3.org/XML/1998/namespace}id'),
                                                           'utterance_ordinal_in_xml': n} for n, e in matches]},
                               'verification_basis': 'Exact text and speaker match in the original XML session after builder normalization; multiple matches are explicitly recorded.'}
    return result


def main():
    os.umask(0o077)
    HERE.chmod(0o700)
    sys.path.insert(0, str(SCRIPTS))
    import run_table3_n100_prompt_identity_repair as repair
    config = repair.load_and_validate_config(CONFIG)
    prompts, guide = repair.prompt_assets(config)
    frozen = {}
    bindings = []
    for ds in config['datasets']:
        truth = {r['packet_id']: r for _, r in rows(ROOT / ds['truth_map'])}
        for line, packet in rows(ROOT / ds['packet_file']):
            key = (ds['run_id'], packet['corpus_id'], packet['packet_id'])
            frozen[key] = (packet, ROOT / ds['packet_file'], line, truth[packet['packet_id']])
        bindings.append({**ds, 'packet_hash_verified': True, 'truth_hash_verified': True})

    packets = []
    inventory = []
    output_inventory = []
    all_paths = set()
    for bank in sorted(BANKS.iterdir()):
        files = sorted((bank / 'by_dataset').glob('*.review_packets.jsonl'))
        if not files:
            continue
        outputs = defaultdict(list)
        for path in sorted(bank.glob('reviewer_outputs*/**/*.json')):
            record = read_json(path)
            if not isinstance(record, dict) or not record.get('packet_id'):
                continue
            all_paths.add(path.resolve())
            item = {'bank': bank.name, 'corpus_id': record['corpus_id'], 'packet_id': record['packet_id'],
                    'role': record.get('role'), 'model': record.get('model_id'), 'status': record.get('status'),
                    'path': str(path), 'url': path.as_uri(), 'prompt_sha256': record.get('prompt_sha256'),
                    'sha256': digest(path.read_bytes())}
            outputs[(record['corpus_id'], record['packet_id'])].append(item)
            output_inventory.append(item)
        bank_ids = set()
        for path in files:
            for line, packet in rows(path):
                key = (bank.name, packet['corpus_id'], packet['packet_id'])
                bank_ids.add((packet['corpus_id'], packet['packet_id']))
                records = outputs.get((packet['corpus_id'], packet['packet_id']), [])
                if not records and key not in frozen:
                    continue
                is_main = key in frozen
                truth = None
                packet_path, packet_line = path, line
                if is_main:
                    packet, packet_path, packet_line, truth = frozen[key]
                entry = {'key': '|'.join(key), 'bank': bank.name, 'corpus_id': packet['corpus_id'],
                         'dataset': NAMES[packet['corpus_id']], 'packet_id': packet['packet_id'],
                         'main_n100': is_main, 'packet_file': link(packet_path), 'packet_line': packet_line,
                         'bank_packet_file': link(path), 'bank_packet_line': line,
                         'packet': packet, 'truth_record': truth, 'outputs': records, 'quality_units': []}
                entry['packet_sha256_canonical'] = digest(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode())
                snapshot = HERE / 'packets' / bank.name / (packet['packet_id'] + '.json')
                write_json(snapshot, packet)
                entry['snapshot'] = link(snapshot)
                if is_main:
                    entry['prompts'] = {}
                    current = []
                    for role, role_prompt in prompts.items():
                        text = repair.build_historical_prompt(role_prompt, guide, packet)
                        sha = digest(text.encode())
                        prompt_path = HERE / 'historical_prompts' / packet['corpus_id'] / packet['packet_id'] / f'{role}.txt'
                        write(prompt_path, text)
                        entry['prompts'][role] = {**link(prompt_path), 'sha256': sha}
                        for model in config['models']:
                            target = repair.output_path(bank / config['repaired_outputs_dir'], role, model, packet['packet_id'])
                            record = read_json(target)
                            assert record['status'] == 'valid', target
                            assert record['prompt_sha256'] == sha, target
                            current.append(str(target))
                    for item in records:
                        item['main_current'] = item['path'] in current
                packets.append(entry)
        assert not (set(outputs) - bank_ids), f'Unmapped reviewer records in {bank}'
        inventory.append({'bank': bank.name, 'datasets': ', '.join(NAMES[c] for c in ORDER if any(k[0] == c for k in bank_ids)),
                          'prepared_packets': len(bank_ids), 'packets_with_outputs': len(outputs),
                          'main_n100_packets': sum(k[0] == bank.name for k in frozen),
                          'stored_output_files': sum(len(v) for v in outputs.values()),
                          'valid_output_files': sum(r['status'] == 'valid' for v in outputs.values() for r in v),
                          'manifest': str(bank / 'manifest.json')})
    # Check filename-based output discovery beyond the known bank paths as well.
    entry_lookup = {(p['bank'], p['corpus_id'], p['packet_id']): p for p in packets}
    early_quality_inventory = []
    outside = []
    for path in (ROOT / 'Storage').rglob('PKT_*.json'):
        if path.resolve() in all_paths or HERE in path.parents:
            continue
        if 'quality_judge' in path.parts and BANKS in path.parents:
            record = read_json(path)
            bank_name = path.relative_to(BANKS).parts[0]
            key = (bank_name, record['corpus_id'], record['packet_id'])
            assert key in entry_lookup, f'Quality-only packet not inventoried: {key}'
            item = {**link(path), 'bank': bank_name, 'corpus_id': record['corpus_id'],
                    'packet_id': record['packet_id'], 'status': record['status'],
                    'judge_model': record['judge_model_id'], 'judged_output_field': record['judged_output_field']}
            early_quality_inventory.append(item)
            entry_lookup[key].setdefault('earlier_quality_outputs', []).append(item)
        else:
            outside.append(str(path))
    assert not outside, f'Unmapped PKT reviewer files: {outside[:5]}'
    packets.sort(key=lambda p: (not p['main_n100'], ORDER.index(p['corpus_id']), p['bank'], p['packet_id']))
    lookup = {(p['corpus_id'], p['packet_id']): p for p in packets if p['main_n100']}
    quality_inventory = []
    for line, unit in rows(QUALITY):
        entry = lookup[(unit['corpus_id'], unit['packet_id'])]
        original = entry['packet']['source_text_context']
        assert [e['text'] for e in unit['payload']['source_context']] == [e['text'] for e in original]
        assert unit['payload']['reviewed_claim']['claim'] == entry['packet']['llm_generated_qualitative_claim']['claim']
        for review in unit['source_reviews']:
            assert digest(Path(review['path']).read_bytes()) == review['sha256'], review['path']
        quality_row = {'corpus_id': unit['corpus_id'], 'packet_id': unit['packet_id'],
                       'method': unit['method'], 'model': unit['reviewer_model_id'], 'unit_id': unit['unit_id'],
                       'units_file': str(QUALITY), 'line': line, 'source_reviews': json.dumps(unit['source_reviews'])}
        quality_inventory.append(quality_row)
        entry['quality_units'].append(quality_row)
        if len(entry['quality_units']) == 1:
            payload_path = HERE / 'quality_input_examples' / entry['corpus_id'] / (entry['packet_id'] + '.json')
            write_json(payload_path, unit)
            entry['quality_input_example'] = link(payload_path)
    assert len(quality_inventory) == 3600
    assert all(len(p['quality_units']) == 9 for p in packets if p['main_n100'])
    print('Inventoried packets and outputs. Verifying source text...', flush=True)
    sources = source_index(packets)
    excerpt_rows = []
    packet_rows = []
    errors = []
    whitespace_differences = []
    for entry in packets:
        packet = entry['packet']
        claim = packet['llm_generated_qualitative_claim']
        packet_rows.append({'scope': 'Table 3 n100' if entry['main_n100'] else 'Earlier observed use',
                            'dataset': entry['dataset'], 'bank': entry['bank'], 'packet_id': entry['packet_id'],
                            'intended_flaw': packet.get('known_intended_flaw_type'), 'research_question': packet['research_question'],
                            'claim': claim['claim'], 'claim_generator_recorded': claim.get('model_id'),
                            'excerpt_count': len(packet['source_text_context']), 'stored_outputs': len(entry['outputs']),
                            'packet_file': entry['packet_file']['path'], 'packet_jsonl_line': entry['packet_line'],
                            'snapshot': entry['snapshot']['path']})
        entry['source_traces'] = []
        for excerpt in packet['source_text_context']:
            src = sources.get((entry['corpus_id'], excerpt['source_record_id']))
            exact_match = src is not None and src['text'] == excerpt['text']
            whitespace_match = (src is not None and isinstance(src['text'], str)
                                and re.sub(r'\s+', ' ', src['text']).strip() == re.sub(r'\s+', ' ', excerpt['text']).strip())
            verified = exact_match or (entry['bank'] == 'draftpkt_20260901T052834Z' and whitespace_match)
            trace = {k: v for k, v in (src or {}).items() if k != 'text'}
            trace['exact_prepared_text_match'] = exact_match
            trace['whitespace_normalized_match'] = whitespace_match
            trace['packet_text_sha256'] = digest(excerpt['text'].encode())
            trace['source_text_sha256'] = digest((src or {}).get('text', '').encode())
            if verified and not exact_match:
                whitespace_differences.append({'packet': entry['key'], 'record': excerpt['source_record_id'],
                                               'difference': 'Whitespace only. Original packet text is preserved, not rewritten.'})
            entry['source_traces'].append(trace)
            if not verified:
                errors.append({'packet': entry['key'], 'record': excerpt['source_record_id']})
            excerpt_rows.append({'scope': packet_rows[-1]['scope'], 'dataset': entry['dataset'], 'bank': entry['bank'],
                                 'packet_id': entry['packet_id'], 'intended_flaw': packet.get('known_intended_flaw_type'),
                                 'display_order': excerpt['display_order'], 'excerpt_id': excerpt['excerpt_id'],
                                 'cited_in_claim': excerpt['excerpt_id'] in claim.get('cited_excerpt_ids', []),
                                 'source_record_id': excerpt['source_record_id'], 'source_id': excerpt['source_id'],
                                 'speaker_id': excerpt.get('speaker_id'), 'text': excerpt['text'],
                                 'local_context_json': json.dumps(excerpt.get('local_context'), ensure_ascii=False),
                                 'metadata_json': json.dumps(excerpt.get('metadata'), ensure_ascii=False),
                                 'source_file': trace.get('raw_file', {}).get('path', ''),
                                 'source_location': trace.get('raw_location', ''),
                                 'source_provenance_json': json.dumps(trace.get('provenance', {})),
                                 'prepared_text_verified': verified, 'exact_prepared_text_match': exact_match})
    assert not errors, errors[:10]
    summary = []
    for corpus in ORDER:
        main = [p for p in packets if p['corpus_id'] == corpus and p['main_n100']]
        all_used = [p for p in packets if p['corpus_id'] == corpus]
        excerpts = [e for p in main for e in p['packet']['source_text_context']]
        flaws = Counter(p['packet']['known_intended_flaw_type'] for p in main)
        assert len(main) == 100 and len(excerpts) == 400 and set(flaws.values()) == {20}
        summary.append({'corpus_id': corpus, 'dataset': NAMES[corpus], 'main_packets': len(main),
                        'main_excerpt_occurrences': len(excerpts),
                        'main_unique_source_records': len({e['source_record_id'] for e in excerpts}),
                        'main_unique_source_ids': len({e['source_id'] for e in excerpts}),
                        'all_observed_bank_packet_entries': len(all_used),
                        'all_observed_unique_packet_ids': len({p['packet_id'] for p in all_used}),
                        'main_flaw_counts': dict(flaws),
                        'historical_split_labels': dict(Counter(e.get('metadata', {}).get('split') for e in excerpts))})
    audit = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'catalog_integrity_checks_passed',
             'scope': 'Stored reviewer outputs in all ten direct packet banks under Storage/draft_review_packets; PKT filename cross-check across Storage. Not all other project research.',
             'manuscript_eligible': False, 'source_text_release_cleared': False, 'summary': summary,
             'observed_bank_packet_entries': len(packets), 'observed_unique_corpus_packet_ids': len({(p['corpus_id'],p['packet_id']) for p in packets}),
             'observed_unique_source_records': len(sources), 'excerpt_occurrences': len(excerpt_rows),
             'source_text_mismatches': errors, 'whitespace_only_source_differences': whitespace_differences,
             'stored_reviewer_output_files': len(output_inventory),
             'stored_output_statuses': dict(Counter(r['status'] for r in output_inventory)),
             'verified_main_reviewer_prompt_hashes': 3600, 'verified_quality_input_units': len(quality_inventory),
             'earlier_quality_output_files': len(early_quality_inventory),
             'main_packet_and_truth_bindings': bindings, 'unmapped_pkt_output_files': outside,
             'source_files': [{'path': str(p), 'sha256': digest(p.read_bytes())} for p in [CONFIG, QUALITY,
                 ROOT / 'dataset/deidentified/dreaddit/records.jsonl', ROOT / 'dataset/deidentified/agyw_focus_groups/records.jsonl',
                 ROOT / 'dataset/raw/goemotions/upstream/train.tsv', ROOT / 'dataset/raw/parlamint_gb/ParlaMint-GB.tgz']],
             'bank_inventory': inventory}
    csv_export('packets_all_observed.csv', packet_rows)
    csv_export('excerpts_all_observed.csv', excerpt_rows)
    csv_export('packets_table3_n100.csv', [r for r in packet_rows if r['scope'] == 'Table 3 n100'])
    csv_export('excerpts_table3_n100.csv', [r for r in excerpt_rows if r['scope'] == 'Table 3 n100'])
    csv_export('bank_inventory.csv', inventory)
    csv_export('reviewer_output_inventory.csv', output_inventory)
    csv_export('quality_input_inventory.csv', quality_inventory)
    if early_quality_inventory:
        csv_export('earlier_quality_output_inventory.csv', early_quality_inventory)
    write_json(HERE / 'audit.json', audit)
    notes = read_json(HERE / 'dataset_notes.json')
    data = {'audit': audit, 'packets': packets, 'notes': notes}
    write_json(HERE / 'catalog.json', data)
    render_viewer(data)
    lines = ['# Verified Inventory', '', f"Snapshot: {audit['created_at_utc']}", '',
             'Counts describe stored artifacts, not independent model calls or independent people.', '',
             '| Dataset | Main packets | Main excerpts | Distinct records | Distinct source IDs | All observed bank-packet entries |',
             '|---|---:|---:|---:|---:|---:|']
    lines += [f"| {s['dataset']} | {s['main_packets']} | {s['main_excerpt_occurrences']} | {s['main_unique_source_records']} | {s['main_unique_source_ids']} | {s['all_observed_bank_packet_entries']} |" for s in summary]
    lines += ['', f"Total: {len(packets)} observed bank-packet entries, {audit['observed_unique_corpus_packet_ids']} unique corpus/packet IDs, {len(excerpt_rows)} excerpt occurrences, {len(sources)} distinct corpus/source-record IDs.",
              '', 'All main sets have exactly 20 packets for each of the five intended flaw types.', '',
              f"Verified {len(excerpt_rows)} excerpt occurrences against source records: {len(excerpt_rows) - len(whitespace_differences)} exact prepared-text matches and {len(whitespace_differences)} whitespace-only match(es) in the initial draft experiment. Packet text is preserved exactly as stored. All main n100 texts match exactly after the recorded source preparation.",
              '', 'Verified all 3,600 repaired reviewer prompt hashes and all 3,600 quality-unit claims/texts and their referenced reviewer file hashes.',
              '', 'These checks establish traceability and file integrity, not flaw validity, blinded evaluation, privacy clearance, or manuscript eligibility.', '',
              '| Bank | Prepared | Observed packets | Main n100 | Stored reviewer files |', '|---|---:|---:|---:|---:|']
    lines += [f"| {r['bank']} | {r['prepared_packets']} | {r['packets_with_outputs']} | {r['main_n100_packets']} | {r['stored_output_files']} |" for r in inventory]
    write(HERE / 'VERIFIED_INVENTORY.md', '\n'.join(lines) + '\n')
    print(json.dumps({k: audit[k] for k in ['status', 'observed_bank_packet_entries', 'observed_unique_corpus_packet_ids', 'excerpt_occurrences', 'stored_reviewer_output_files']}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-only', action='store_true', help='Rebuild only index.html from the existing catalog; leave data and experiments unchanged.')
    args = parser.parse_args()
    if args.render_only:
        data = read_json(HERE / 'catalog.json')
        assert len([packet for packet in data['packets'] if packet['main_n100']]) == 400
        render_viewer(data)
        print(json.dumps({'status': 'viewer_rendered', 'data_changed': False, 'output': str(HERE / 'index.html')}))
    else:
        main()
