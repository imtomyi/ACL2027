"""Schedule the ACE-AppWorld Qwen3-8B reproduction across the owned GPU streams.

One job shard runs per GPU stream at a time. Evaluation jobs are split into task chunks with the
upstream num_processes/process_index mechanism; adaptation and online jobs stay single serial
streams. Offline evaluations start only after their adaptation has written its final playbook.
While the v5 chain is alive only the early jobs may use the early GPUs; afterwards every stream is used.
"""
from pathlib import Path
import argparse, fcntl, json, os, re, subprocess, time

SHARDS = 8
ATTEMPTS = 3
# Offline adaptations come first: they produce the trained playbooks needed earliest and gate the offline evaluations.
PRIORITY = ['qwen3_8b_ACE_offline_with_GT_adaptation', 'qwen3_8b_ACE_offline_no_GT_adaptation',
            'qwen3_8b_ACE_online_no_GT_test_challenge', 'qwen3_8b_ACE_online_no_GT_test_normal',
            'qwen3_8b_ReAct_test_challenge', 'qwen3_8b_ReAct_test_normal',
            'qwen3_8b_ACE_offline_with_GT_evaluation_test_challenge', 'qwen3_8b_ACE_offline_no_GT_evaluation_test_challenge',
            'qwen3_8b_ACE_offline_with_GT_evaluation_test_normal', 'qwen3_8b_ACE_offline_no_GT_evaluation_test_normal']


def load(path): return json.loads(Path(path).read_text())


def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp'); temporary.write_text(json.dumps(value, indent=2)+'\n'); temporary.replace(path)


def identity(pid):
    try: return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19]
    except FileNotFoundError: return None


def alive(pid): return pid is not None and Path(f'/proc/{pid}').exists()


def owned_ports(parent):
    """Map owned GPU streams to ports, excluding any GPU running another account's process."""
    ownership = load(parent/'services/ownership.json')['services']
    for s in ownership:
        if identity(s['pid']) != s['start_identity']: raise RuntimeError('Owned model service changed')
    listing = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True)
    by_uuid, foreign = {s['uuid']: s for s in ownership}, set()
    for line in listing.splitlines():
        parts = [v.strip() for v in line.split(',')]
        if len(parts) != 2 or parts[0] not in by_uuid: continue
        try: environment = Path(f'/proc/{int(parts[1])}/environ').read_bytes()
        except FileNotFoundError: continue
        except PermissionError: foreign.add(parts[0]); continue
        if f'OLLAMA_HOST=127.0.0.1:{by_uuid[parts[0]]["port"]}'.encode() not in environment: foreign.add(parts[0])
    return ({s['gpu']: s['port'] for s in ownership if s['uuid'] not in foreign},
            sorted(by_uuid[u]['gpu'] for u in foreign))


def scores(text):
    """Parse the aggregate row of the official AppWorld evaluation report."""
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip('│|').replace('│', '|').split('|')]
        if cells and cells[0] == 'aggregate' and len(cells) >= 3:
            return dict(task_goal_completion=float(cells[1]), scenario_goal_completion=float(cells[2]))
    return None


class Orchestrator:
    def __init__(self, root, parent, tokenizer, early_gpus, chain_pid):
        self.root, self.parent, self.tokenizer = root, parent, tokenizer
        self.early_gpus, self.chain_pid = set(early_gpus), chain_pid
        self.jobs = load(root/'jobs.json')
        self.state_path = root/'orchestrator/state.json'
        self.state = load(self.state_path) if self.state_path.exists() else dict(units={}, jobs={})
        for name in PRIORITY:
            job = self.jobs[name]
            shards = SHARDS if job['kind'] == 'evaluation' else 1
            for i in range(shards):
                self.state['units'].setdefault(f'{name}#{i}', dict(job=name, shard=i, shards=shards, status='pending', attempts=0))
            self.state['jobs'].setdefault(name, dict(status='pending', kind=job['kind'], split=job['split']))
        self.running = {}

    def ready(self, unit):
        job = self.jobs[unit['job']]
        return all(self.state['jobs'][d]['status'] == 'complete' and Path(self.jobs[d]['final_playbook']).exists()
                   for d in job['depends'])

    def services(self):
        """Owned streams without another account's GPU process; re-checked every step so freed GPUs return."""
        ports, excluded = owned_ports(self.parent)
        self.state['excluded_gpus_with_foreign_processes'] = excluded
        return ports

    def launch(self, key, unit, gpu, port):
        job = self.jobs[unit['job']]; log = self.root/'logs'/f'{key.replace("#", "_")}.log'; log.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, APPWORLD_PROJECT_PATH=str(self.root/'source'), PYTHONPATH=str(self.root/'code'),
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
                   ACE_NATIVE_ENDPOINT=f'http://127.0.0.1:{port}', ACE_NATIVE_CALLS=str(self.root/'calls'/unit['job']),
                   ACE_NATIVE_TOKENIZER=self.tokenizer)
        if job.get('final_playbook'): env['ACE_FINAL_PLAYBOOK'] = job['final_playbook']
        with log.open('ab') as handle:
            proc = subprocess.Popen([str(self.root/'venv/bin/python'), str(self.root/'code/run_native.py'), 'run', unit['job'],
                '--num-processes', str(unit['shards']), '--process-index', str(unit['shard'])],
                cwd=self.root/'source', env=env, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle, start_new_session=True)
        unit.update(status='running', gpu=gpu, pid=proc.pid, started_at=time.time(), attempts=unit['attempts']+1)
        self.running[gpu] = (key, proc)

    def finish_job(self, name):
        job, record = self.jobs[name], self.state['jobs'][name]
        if job['kind'] in ['evaluation', 'online']:
            result = subprocess.run([str(self.root/'venv/bin/appworld'), 'evaluate', name, job['split']], cwd=self.root/'source',
                env=dict(os.environ, APPWORLD_PROJECT_PATH=str(self.root/'source')), capture_output=True, text=True)
            (self.root/'evaluations').mkdir(exist_ok=True)
            (self.root/'evaluations'/f'{name}.txt').write_text(result.stdout+result.stderr)
            record.update(evaluation_exit=result.returncode, **(scores(result.stdout) or {}))
        if job.get('final_playbook'):
            path = Path(job['final_playbook']); live = path.parent/'playbook.txt'
            record.update(final_playbook=str(path), final_playbook_chars=len(path.read_text()) if path.exists() else None,
                          # Upstream rewrites playbook.txt after every curation; the post-loop copy must match it.
                          final_matches_curated_file=path.exists() and live.exists() and path.read_text() == live.read_text())
        record.update(status='complete' if record.get('evaluation_exit', 0) == 0 else 'evaluation_failed', completed_at=time.time())

    def step(self):
        stopped = (self.root/'STOP').exists() or (self.parent/'STOP').exists()
        early = alive(self.chain_pid)
        for gpu, (key, proc) in list(self.running.items()):
            code = proc.poll()
            if code is None: continue
            unit = self.state['units'][key]; del self.running[gpu]
            unit.update(ended_at=time.time(), exit_code=code)
            unit['status'] = 'done' if code == 0 else ('pending' if unit['attempts'] < ATTEMPTS and not stopped else 'failed')
        for name in PRIORITY:
            record = self.state['jobs'][name]
            shards = [u for u in self.state['units'].values() if u['job'] == name]
            if record['status'] == 'pending' and any(u['status'] in ['running', 'done'] for u in shards): record['status'] = 'running'
            if record['status'] == 'running' and all(u['status'] == 'done' for u in shards): self.finish_job(name)
            if record['status'] in ['pending', 'running'] and any(u['status'] == 'failed' for u in shards): record['status'] = 'failed'
        if not stopped:
            ports = self.services()
            for gpu, (key, proc) in list(self.running.items()):
                if gpu in ports: continue
                # Yield a GPU another account started using; the shard resumes later by cache replay.
                os.killpg(proc.pid, 15); proc.wait()
                unit = self.state['units'][key]; del self.running[gpu]
                unit.update(status='pending', attempts=max(0, unit['attempts']-1), preemptions=unit.get('preemptions', 0)+1,
                            ended_at=time.time())
            allowed = (self.early_gpus if early else set(ports)) & set(ports)
            for gpu in sorted(allowed - set(self.running)):
                candidates = [(k, u) for k, u in self.state['units'].items() if u['status'] == 'pending' and self.ready(u)
                              and (not early or self.jobs[u['job']]['kind'] == 'adaptation')]
                if not candidates: break
                key, unit = min(candidates, key=lambda x: (PRIORITY.index(x[1]['job']), x[1]['shard']))
                self.launch(key, unit, gpu, ports[gpu])
        self.state.update(early_phase=early, stop_requested=stopped, active={str(g): k for g, (k, _) in self.running.items()},
                          updated_at=time.time())
        atomic(self.state_path, self.state)
        terminal = all(u['status'] in ['done', 'failed'] for u in self.state['units'].values())
        return (terminal or stopped) and not self.running


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--tokenizer', required=True)
    parser.add_argument('--early-gpus', default='6,7')
    parser.add_argument('--chain-pid', type=int)
    args = parser.parse_args(); os.umask(0o077)
    lock = (args.root/'orchestrator.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run = Orchestrator(args.root, args.parent, args.tokenizer, [int(g) for g in args.early_gpus.split(',')], args.chain_pid)
    for key, unit in run.state['units'].items():
        # A unit left running by an interrupted orchestrator restarts; cached calls replay without new inference.
        if unit['status'] == 'running':
            if alive(unit.get('pid')): raise RuntimeError('Existing live shard needs recovery: '+key)
            unit['status'] = 'pending'
    while not run.step():
        time.sleep(15)
    print(json.dumps({k: v['status'] for k, v in run.state['jobs'].items()}))
