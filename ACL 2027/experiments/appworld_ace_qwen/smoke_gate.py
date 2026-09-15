"""Development gate with the real Qwen3-8B runtime on dev/train tasks only; no test task is run.

Passes when every smoke run exits cleanly after real model calls and the official evaluator
reports on the evaluated runs. Latency, context exhaustion and playbook change are recorded to
size the production schedule; they do not gate.
"""
from pathlib import Path
import argparse, json, os, statistics, subprocess, time
from orchestrate import scores

RUNS = [('smoke_ReAct', 'qwen3_8b_ReAct_test_normal', 'dev', None),
        ('smoke_ACE_offline_with_GT', 'qwen3_8b_ACE_offline_with_GT_adaptation', 'train', 'offline_with_GT'),
        ('smoke_ACE_online_no_GT', 'qwen3_8b_ACE_online_no_GT_test_normal', 'dev', 'online')]


def main(root, gpus, tokenizer):
    source, smoke = root/'source', root/'smoke'
    dev, train = [(source/'data/datasets'/f'{s}.txt').read_text().split()[0] for s in ['dev', 'train']]
    configs = source/'experiments/configs'
    procs = {}
    for index, (name, origin, dataset, playbook) in enumerate(RUNS):
        config = json.loads((configs/f'{origin}.jsonnet').read_text())
        config['config']['dataset'] = dataset; config['config']['task_ids'] = [dev if dataset == 'dev' else train]
        if playbook:
            path = smoke/'playbooks'/playbook/'playbook.txt'; path.parent.mkdir(parents=True, exist_ok=True)
            config['config']['agent']['trained_playbook_file_path'] = str(path)
        (configs/f'{name}.jsonnet').write_text(json.dumps(config, indent=2))
        gpu = gpus[index % len(gpus)]
        env = dict(os.environ, APPWORLD_PROJECT_PATH=str(source), PYTHONPATH=str(root/'code'), HF_HUB_OFFLINE='1',
                   TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false', ACE_NATIVE_ENDPOINT=f'http://127.0.0.1:{11840+gpu}',
                   ACE_NATIVE_CALLS=str(smoke/'calls'/name), ACE_NATIVE_TOKENIZER=tokenizer,
                   ACE_FINAL_PLAYBOOK=str(smoke/'playbooks'/name/'final.txt'))
        log = (smoke/f'{name}.log').open('wb')
        procs[name] = (subprocess.Popen([str(root/'venv/bin/python'), str(root/'code/run_native.py'), 'run', name,
            '--num-processes', '1', '--process-index', '0'], cwd=source, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=log), gpu, time.time())
    report = {}
    initial = (source/'experiments/playbooks/appworld_initial_playbook.txt').read_text()
    for name, (proc, gpu, started) in procs.items():
        code = proc.wait()
        calls = [json.loads(p.read_text()) for p in (smoke/'calls'/name).glob('*.json')]
        events = [json.loads(x) for x in (smoke/'calls'/name/'events.jsonl').read_text().splitlines()] if (smoke/'calls'/name/'events.jsonl').exists() else []
        row = dict(gpu=gpu, exit_code=code, minutes=(time.time()-started)/60, model_calls=len(calls),
                   seconds_per_call_median=statistics.median(c['seconds'] for c in calls) if calls else None,
                   input_tokens_max=max((c['input_tokens'] for c in calls), default=None),
                   context_exhausted=sum(e['kind'] == 'context_exhausted' for e in events),
                   output_ceiling=sum(e['kind'] == 'output_ceiling' for e in events))
        if name != 'smoke_ACE_offline_with_GT':
            result = subprocess.run([str(root/'venv/bin/appworld'), 'evaluate', name, 'on_only', '--task-id', dev], cwd=source,
                                    env=dict(os.environ, APPWORLD_PROJECT_PATH=str(source)), capture_output=True, text=True)
            row.update(evaluate_exit=result.returncode, evaluation=scores(result.stdout))
        playbook = smoke/'playbooks'/name/'final.txt'
        if playbook.exists(): row.update(playbook_chars=len(playbook.read_text()), playbook_changed=playbook.read_text() != initial)
        report[name] = row
    passed = all(r['exit_code'] == 0 and r['model_calls'] > 0 and r.get('evaluate_exit', 0) == 0 for r in report.values())
    value = dict(passed=passed, runs=report, dev_task=dev, train_task=train, at=time.time())
    (smoke/'report.json').write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps(value))
    return passed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--gpus', required=True)
    parser.add_argument('--tokenizer', required=True)
    args = parser.parse_args()
    raise SystemExit(0 if main(args.root, [int(g) for g in args.gpus.split(',')], args.tokenizer) else 1)
