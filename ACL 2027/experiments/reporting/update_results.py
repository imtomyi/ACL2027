"""Refresh the shared diagnostic report without modifying any experiment state."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os

ROOT = Path(__file__).resolve().parents[2]
STORAGE = ROOT / 'Storage'
RUNS = [
    ('Dreaddit', STORAGE/'dreaddit_icl/comparison_run_20260912'),
    ('GoEmotions', STORAGE/'goemotions_offline/run_20260912'),
    ('CaChe and ParlaMint-GB', STORAGE/'paired_feedback/run_20260912'),
]

def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}

def write_atomic(path, text):
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(text)
    temp.replace(path)

def main():
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    go = RUNS[1][1]
    queue = read_json(go/'queue.json')
    method = queue.get('method', 'unknown')
    state = read_json(go/method/'state.json')
    n = state.get('n', queue.get('n', 0))
    alive = False
    if queue.get('pid'):
        try: os.kill(queue['pid'], 0); alive = True
        except ProcessLookupError: pass
    recent = state.get('recent_seconds', [])[-20:]
    summary = f"GoEmotions: {method}, {queue.get('stage', 'unknown')}, {n}/5427; queue {queue.get('status', 'unknown')}; process {'alive' if alive else 'not running'}."
    if recent and queue.get('stage') == 'prediction' and queue.get('status') == 'running':
        average = sum(recent)/len(recent)
        minutes = round(max(0, 5427-n)*average/60)
        summary += f' Recent {len(recent)} examples: {average:.2f} s/example; provisional prediction ETA {minutes//60} h {minutes%60} min. Overall experiment ETA is unknown.'
    health=read_json(STORAGE/'experiment_monitor/health.json')
    monitor_note=''
    if health:
        checked=datetime.fromtimestamp(health['observed_at'],ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
        monitor_note=f"Last health check: **{health['classification']}**, at {checked}. Recovery is enabled for diagnosed operational failures. [Recovery rules](<{STORAGE/'experiment_monitor/RECOVERY.md'}>).\n\n"
    paired = RUNS[2][1]
    annotations = sum(len(list((paired/'references'/f'{c}_{split}').glob('*.json')))
                      for c in ['cache', 'parlamint_gb'] for split in ['adapt', 'test'])
    chunks = []
    for title, run in RUNS:
        content = (run/'METRICS.md').read_text()
        content = '\n'.join(content.splitlines()[1:]).strip()
        status = read_json(run/'queue.json').get('status', 'unknown')
        section = f'## {title}\n\nQueue: **{status}**. [Run-specific metrics](<{run / "METRICS.md"}>).\n\n'
        if run == paired:
            section += f'Reference annotations saved: **{annotations}/600**. This run is paused while GoEmotions has priority.\n\n'
        chunks.append(section + content)
    prefix = f'# Four-dataset experimental results\n\nUpdated: **{now}**. This shared snapshot refreshes with the five-minute monitor; per-run reports can be newer.\n\n{summary}\n\n'
    prefix += monitor_note + 'Diagnostic and exploratory records only. Pending results stay blank. No manuscript result is filled from this report.\n\n'
    prefix += f'[Metric definitions and interpretation](<{STORAGE / "METRICS.md"}>).\n\n'
    results = prefix + '\n\n'.join(chunks) + '\n'
    definitions = f'''# Four-dataset metrics and current results

Updated: **{now}**. [Shared results](<{STORAGE / 'RESULTS.md'}>).

- Dreaddit Acc: stress-label accuracy over all 712 test examples.
- GoEmotions Acc: exact equality of the complete emotion-label set over all 5,427 test examples. Micro-F1 pools label decisions; macro-F1 averages the 28 label scores. Invalid predictions count as wrong for Acc and as an empty set for F1.
- CaChe and ParlaMint-GB: human-GT Acc/F1 are N/A. Reference agreement is exact topic-set agreement with frozen, unverified Qwen3-8B annotations. Invalid topic outputs count as nonagreement. It is not independent ground-truth accuracy.
- GT ✓ uses dataset reference labels in Dreaddit/GoEmotions. GT ✓† in CaChe/ParlaMint means model-generated reference feedback, not human ground truth. GT ✗ provides no reference feedback to adaptation.
- Offline methods adapt before evaluation and freeze the resulting context. Online methods predict the current example before its feedback can update memory for subsequent examples.
- Conformability is the same-family LLM source-grounding pass rate: traceable basis, faithful meaning, supported scope and no invented facts. The judge does not receive reference labels or method identity; its outcomes never feed adaptation. It is not human validation.
- Final percentages require the complete evaluation denominator. Unresolved judgments are displayed, never silently excluded or converted into failures. Partial progress is not a final score.
- CaChe/ParlaMint use a 100-adaptation / 200-evaluation pilot per corpus with provisional topic codebooks. They are not full-corpus benchmark runs. The same teacher/generator/judge family can share errors.
- Current implementations cover different method subsets across corpora, as listed below. Missing methods and GPT-5 are not represented as completed experiments. These are task transfers, not exact reproductions of the finance-paper results.

'''
    write_atomic(STORAGE/'RESULTS.md', results)
    write_atomic(STORAGE/'METRICS.md', definitions + monitor_note + '\n\n'.join(chunks) + '\n')
    # Keep the originally shared Dreaddit report navigable; preserve its run-specific results.
    legacy = RUNS[0][1]/'RESULTS.md'
    marker = '<!-- shared-results-navigation -->'
    original = legacy.read_text()
    if marker not in original:
        note = f'{marker}\n**All four datasets:** [live shared RESULTS.md](<{STORAGE / "RESULTS.md"}>) · [METRICS.md](<{STORAGE / "METRICS.md"}>). This file below covers Dreaddit only.\n\n'
        write_atomic(legacy, note + original)
    print(json.dumps(dict(updated_at=now,method=method,n=n,total=5427,process_alive=alive,
                         paired_annotations=annotations,results=str(STORAGE/'RESULTS.md'),metrics=str(STORAGE/'METRICS.md'))))

if __name__ == '__main__': main()
