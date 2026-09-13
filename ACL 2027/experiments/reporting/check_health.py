"""Persist metadata-only health observations for the recovery-capable heartbeat.

This detector never kills, launches or changes an experiment. The heartbeat agent
diagnoses flagged conditions and performs bounded, checkpoint-preserving repair.
"""
from pathlib import Path
import fcntl
import json
import os
import statistics
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'Storage/goemotions_offline/run_20260912'
MONITOR = ROOT/'Storage/experiment_monitor'

def read(path):
    return json.loads(path.read_text()) if path.exists() else {}

def classify(status, process_matches, stage, idle_seconds, median_seconds=0,
             confirmed_updates=0, previous_same_stage=False, slower=False):
    if status=='complete':return 'complete', None
    if status=='paused':return 'paused', None
    if status=='failed':return 'failed', 'Diagnose saved error and repair before resuming.'
    if status!='running':return 'unknown', 'Inspect state; do not guess that work should start.'
    if not process_matches:return 'missing_process', 'Check process inventory and checkpoint lock before recovery.'
    threshold=max(900 if stage=='optimization' else 300,10*median_seconds)
    if idle_seconds>=threshold:
        return 'suspected_stall', f'No confirmed work for {int(idle_seconds)} s; investigate before interrupting.'
    if slower and confirmed_updates>0 and previous_same_stage:
        return 'slowdown', 'Work is progressing; inspect resource contention, do not restart solely for slow speed.'
    return 'healthy', None

def main():
    if (ROOT/'Storage/budget_pilot/ACTIVE.json').exists():
        import runpy
        runpy.run_path(str(ROOT/'experiments/budget_pilot/health.py'),run_name='__main__')
        return
    os.umask(0o077);MONITOR.mkdir(parents=True,exist_ok=True)
    lock=(MONITOR/'observation.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX)
    now=time.time();q=read(RUN/'queue.json');method=q.get('method','');stage=q.get('stage','')
    if method not in ['base','icl','miprov2','gepa']:method=''
    directory=RUN/method if method else RUN
    s=read(directory/'state.json');quality=read(directory/'quality_state.json')
    previous=read(MONITOR/'health.json')
    call_count=0;last_call=0
    for p in directory.rglob('calls.jsonl'):
        # Calls are append-only metadata. Ignore an in-flight unterminated line.
        with p.open('rb') as handle:call_count+=sum(line.endswith(b'\n') for line in handle)
        last_call=max(last_call,p.stat().st_mtime)
    n=quality.get('n',0) if stage=='conformability' else s.get('n',q.get('n',0))
    recent=(quality if stage=='conformability' else s).get('recent_seconds',[])[-20:]
    median=statistics.median(recent) if recent else 0
    key=[method,stage,q.get('pid')]
    same=previous.get('key')==key
    count_key=[n,call_count]
    changed=not same or previous.get('count_key')!=count_key
    last_work=max(last_call,float(q.get('updated_at',0)))
    state_path=directory/('quality_state.json' if stage=='conformability' else 'state.json')
    if state_path.exists():last_work=max(last_work,state_path.stat().st_mtime)
    if same and not changed:last_work=previous.get('last_confirmed_progress_at',last_work)
    if not last_work:last_work=now
    baseline=previous.get('baseline_median_seconds',0) if same else 0
    if not baseline and len(recent)>=20:baseline=median
    updates=max(0,n-previous.get('n',n)) if same else 0
    matches=False
    if q.get('pid'):
        proc=subprocess.run(['ps','-p',str(q['pid']),'-o','command='],capture_output=True,text=True,timeout=5)
        matches=proc.returncode==0 and str(ROOT/'experiments/goemotions_offline/run.py') in proc.stdout
    status,action=classify(q.get('status'),matches,stage,max(0,now-last_work),median,
                           updates,same,bool(baseline and median>3*baseline))
    server='unknown'
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/ps',timeout=3) as response:
            data=json.load(response)
        server='reachable';model_loaded=any(m.get('name')=='qwen3:8b' for m in data.get('models',[]))
    except Exception:
        server='unreachable';model_loaded=None
    health=dict(observed_at=now,key=key,count_key=count_key,method=method,stage=stage,n=n,total=5427,
        queue_status=q.get('status'),process_matches=matches,classification=status,suggested_action=action,
        completed_calls=call_count,confirmed_item_increase=updates,last_confirmed_progress_at=last_work,
        no_progress_seconds=max(0,now-last_work),median_seconds=median,baseline_median_seconds=baseline,
        ollama=server,model_loaded=model_loaded,
        interpretation='No-progress duration is diagnostic evidence, not automatically confirmed wasted time.')
    temp=MONITOR/'health.tmp';temp.write_text(json.dumps(health,indent=2)+'\n');temp.replace(MONITOR/'health.json')
    with (MONITOR/'observations.jsonl').open('a') as h:h.write(json.dumps(health)+'\n')
    print(json.dumps(health))

if __name__=='__main__':main()
