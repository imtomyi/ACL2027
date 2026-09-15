"""Compact presentation of measured results, separate from detailed metrics."""
from pathlib import Path

NAMES = {'dreaddit': 'Dreaddit', 'goemotions': 'GoEmotions',
         'cache': 'CaChe', 'parlamint_gb': 'ParlaMint-GB'}
METHODS = {'base': 'Qwen3 8B Base', 'icl': 'ICL', 'miprov2': 'MIPROv2',
           'gepa': 'GEPA', 'ace_offline_no_gt': 'ACE',
           'dc_online_ref': 'DC (CU)', 'dc_online_no_gt': 'DC (CU)',
           'ace_online_ref': 'ACE', 'ace_online_no_gt': 'ACE'}


def row_status(row, supervisor):
    entry = supervisor.get('corpora', {}).get(row['corpus'], {})
    phase = entry.get('phases', {}).get(row['phase'], {}).get('status', 'queued')
    predictions_done = row['predicted'] == 100
    updates_done = row['phase'] == 'offline' or row['updated'] == 100
    if predictions_done and updates_done and row['judged'] == 100 and not row['unknown']:
        return 'Complete'
    if (supervisor.get('status') == 'paused'
            and supervisor.get('corpus') == row['corpus']
            and entry.get('phase') == row['phase']
            and row['method'] == row['queue_method']):
        return ('Paused: low disk space' if supervisor.get('pause_reason') in ('disk_full_ENOSPC','low_disk_space')
                else 'Paused')
    active = (entry.get('status') == 'running' and entry.get('phase') == row['phase']
              and phase == 'running' and row['method'] == row['queue_method'])
    if active:
        return 'Running: ' + row['queue_stage'].replace('_', ' ')
    if phase in ('failed', 'budget_exhausted'):
        if phase == 'failed':
            return 'Failed' if row['method'] == row['queue_method'] or row['predicted'] else 'Not started: phase failed'
        return 'Time limit reached'
    if row['unknown']:
        return 'Unresolved judgments'
    if predictions_done and updates_done:
        return 'Awaiting judging'
    if row['predicted']:
        return 'Queued to resume'
    return 'Queued'


def render(rows, supervisor, now, storage, policy, metrics_path, history=False):
    storage = Path(storage)
    complete = sum(row_status(r, supervisor) == 'Complete' for r in rows)
    text = '# Experiment results · N=100 per dataset\n\n'
    text += f'Updated: **{now}**. Refreshed by the five-minute monitor.\n\n'
    text += ('**400 unique evaluation items: Dreaddit 100 · GoEmotions 100 · CaChe 100 · '
             'ParlaMint-GB 100.** Every method and both phases reuse the same ordered '
             '100 items per dataset. Training and adaptation examples are separate.\n\n')
    text += f'**Fully evaluated rows in this report: {complete}/{len(rows)}.** A row is complete only after prediction, required online updates, and all 100 resolved judgments.\n\n'
    if policy.get('uniform_policy'):
        text += ('**Fresh uniform protocol:** all 24 rows restart from empty state with new run-local caches. '
                 'Prediction/generator/optimizer/reflector start at 4,096 output tokens; curator at 8,192; judge at 384. '
                 'The same predeclared length-only retry rule doubles non-judge caps up to 16,384 within context 32,768. '
                 'No truncated answer is accepted. ACE/DC memory is bounded at 4,096 tokens; oversized updates retain the previous valid memory. '
                 'Earlier scores remain separate. [Frozen protocol](<' + str(storage/'budget_pilot'/policy['run_id']/'PROTOCOL.md') + '>).\n\n')
    if policy.get('output_cap_recovery'):
        text += ('**Output-limit recovery v1:** user-authorized continuation of failed rows from preserved checkpoints. '
                 'New generator/prediction/reflector calls reserve up to 4,096 output tokens and curator calls 8,192, '
                 'with bounded escalation to at most 16,384 within the 32,768-token context. '
                 'Completed earlier outputs are reused; these rows mix original and revised output budgets and are not a uniform-budget rerun. '
                 'Model, prompts, seed, evaluation IDs and judge remain unchanged. '
                 '[Revision and per-row boundaries](<' + str(storage/'experiment_monitor/incidents/output_cap_recovery_20260914/REVISION.md') + '>).\n\n')
    if supervisor.get('status') == 'finished':
        failed = sum(row_status(r, supervisor) == 'Failed' for r in rows)
        not_started = sum(row_status(r, supervisor) == 'Not started: phase failed' for r in rows)
        text += (f'**Scheduler ended:** {failed} rows failed; {not_started} rows were not started because their phase failed. '
                 'No worker is running. Scheduler termination does not imply all experiments completed.\n\n')
    if supervisor.get('status') == 'paused' and supervisor.get('pause_reason') in ('disk_full_ENOSPC','low_disk_space'):
        text += ('**Storage block:** the experiment worker is stopped because available disk space is insufficient. '
                 'Saved results are retained. Restart is held until at least 3 GiB is free; '
                 'the authorized time policy remains unchanged.\n\n')
    active = [r for r in rows if row_status(r, supervisor).startswith('Running:')]
    for r in active:
        text += (f'**Current:** {NAMES[r["corpus"]]} · {r["phase"]} · {METHODS[r["method"]]} '
                 f'GT {r["gt"]} · {row_status(r, supervisor)}.\n\n')
    text += 'Execution priority: ' + ' → '.join(NAMES[c] for c in policy.get('corpus_order',['cache','parlamint_gb','goemotions','dreaddit'])) + '.\n\n'
    text += ('Offline and online prioritize completing every scheduled 100-item evaluation and its judgments. The user authorized additional time; the previous two-hour cutoff is disabled.\n\n'
             if policy.get('offline_priority') == policy.get('online_priority') == 'complete_100' else
             'Online continues to 100 items; offline retains its time limit.\n\n'
             if policy.get('online_priority') == 'complete_100' else
             'The existing two-hour limit per dataset is shared across offline and online. '
             'Rows stopped by the limit remain incomplete with denominator 100.\n\n')
    text += '## Results and progress\n\n'
    text += ('Acc and Conformability are percentages. **—** = not yet final; **N/A** = metric not applicable to the current evaluation. '
             'Predicted, updated, and judged are separate counts, each out of 100.\n\n')
    text += ('The four ACE/AppWorld metric columns are included for reference. They are N/A for these corpora: '
             'the current evaluation has no official AppWorld Normal/Challenge splits, executable task-success tests, '
             'or scenario groups. N/A is not zero or a pending score.\n\n')
    for corpus, name in NAMES.items():
        selected = [r for r in rows if r['corpus'] == corpus]
        if not selected:
            continue
        text += f'### {name}\n\n'
        text += '| Phase | Method | GT | Acc % | Conformability % | Test-Normal TGC↑ | Test-Normal SGC↑ | Test-Challenge TGC↑ | Test-Challenge SGC↑ | Predicted | Updated | Judged | Unresolved | Status |\n'
        text += '| --- | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |\n'
        for r in selected:
            updated = f'{r["updated"]}/100' if r['phase'] == 'online' else '—'
            text += (f'| {r["phase"].title()} | {METHODS[r["method"]]} | {r["gt"]} | '
                     f'{r["acc"]} | {r["conf"]} | N/A | N/A | N/A | N/A | {r["predicted"]}/100 | {updated} | '
                     f'{r["judged"]}/100 | {r["unknown"]} | {row_status(r, supervisor)} |\n')
        text += '\n'
    text += '## Reading these results\n\n'
    text += ('- Model: Qwen3 8B Q4_K_M, thinking off, seed 42. GPT-5 is outside the current queue.\n'
             '- Dreaddit Acc compares stress labels. GoEmotions Acc requires an exact match of the full emotion-label set.\n'
             '- CaChe and ParlaMint-GB use GT ✗ only. Acc is N/A; no reference labels are generated.\n'
             '- GT ✓ supplies labels for adaptation; GT ✗ does not. Offline context is frozen before evaluation; online feedback follows each saved prediction.\n'
             '- Conformability measures source grounding using a reference-blind judge from the same model family. It is not human validation.\n'
             '- ACE reports AppWorld Task Goal Completion (TGC: all tests pass for a task) and Scenario Goal Completion (SGC: all tasks in a scenario succeed). These are not substitutes for Acc or Conformability. See [ACE, evaluation metrics](https://arxiv.org/html/2510.04618v1#S4.SS1) and [AppWorld, evaluation and splits](https://arxiv.org/html/2407.18901v1).\n'
             '- Compatible saved predictions are reused and scores recomputed for these 100 IDs. Earlier smaller-run scores are not substituted. These are local task transfers, not exact paper reproductions.\n\n')
    text += f'[Detailed metrics, F1 and run settings](<{metrics_path}>).\n\n'
    if history:
        text += '## Earlier runs · separate protocols\n\nDo not combine these scores with the current N=100 results.\n\n'
        for name, path in [('24/128/8-item pilot', 'budget_pilot/run_20260913'),
                           ('Dreaddit full test', 'dreaddit_icl/comparison_run_20260912'),
                           ('GoEmotions full test', 'goemotions_offline/run_20260912'),
                           ('Earlier paired-corpus experiment', 'paired_feedback/run_20260912')]:
            text += f'- [{name}](<{storage/path/"METRICS.md"}>)\n'
    if policy.get('uniform_policy'):
        text=text.replace('Compatible saved predictions are reused and scores recomputed for these 100 IDs. Earlier smaller-run scores are not substituted.', 'No earlier predictions, judgments, optimizer artifacts or playbooks are reused in this uniform run.')
        if history:text += '\n[Archived earlier N=100 results](<' + str(storage/'experiment_monitor/incidents/output_cap_recovery_20260914/prior_RESULTS.md') + '>).\n'
    return text
