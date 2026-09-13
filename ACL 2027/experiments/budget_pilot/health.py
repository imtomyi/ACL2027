"""Metadata-only health for the user-selected bounded pilot supervisor."""
from pathlib import Path
import json,subprocess,time,urllib.request,statistics,os,fcntl
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'Storage/budget_pilot/run_20260913';MON=ROOT/'Storage/experiment_monitor'
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def matches(pid,script):
    if not pid:return False
    p=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True,timeout=5)
    return p.returncode==0 and script in p.stdout

def main():
    lock=(MON/'observation.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX)
    now=time.time();sup=read(RUN/'supervisor.json');c=sup.get('corpus');entry=sup.get('corpora',{}).get(c,{})
    d=RUN/c if c else RUN;q=read(d/'queue.json');method=q.get('method');stage=q.get('stage')
    md=d/method if c in ('goemotions','dreaddit') and method else d/c/method if c and method and method!='reference_annotator' else d/'references'
    if method and method.startswith('reference_'):md=d/'references'
    state=read(md/('quality_state.json' if stage=='conformability' else 'state.json'))
    calls=0;last=0
    for p in md.rglob('calls.jsonl'):
        with p.open('rb') as h:calls+=sum(x.endswith(b'\n') for x in h)
        last=max(last,p.stat().st_mtime)
    n=state.get('n',q.get('n',0));key=[c,method,stage,entry.get('pid')];count=[n,calls,state.get('adapted',0)]
    old=read(MON/'health.json');same=old.get('key')==key
    if same and old.get('count_key')==count:last=old.get('last_confirmed_progress_at',last)
    else:last=max(last,float(q.get('updated_at',0)))
    idle=max(0,now-last) if last else 0
    recent=state.get('recent_seconds',[])[-20:];median=statistics.median(recent) if recent else 0
    supervisor_alive=matches(sup.get('pid'),str(ROOT/'experiments/budget_pilot/supervise.py'))
    child_alive=matches(entry.get('pid'),entry.get('script','/nonexistent'))
    status='healthy'
    if sup.get('status')=='finished':status='finished'
    elif sup.get('status')=='paused':status='paused'
    elif not supervisor_alive:status='missing_supervisor'
    elif entry.get('status')=='running' and not child_alive:status='transition_or_missing_child'
    elif q.get('status')=='failed':status='failed'
    elif idle>=max(900 if stage=='optimization' else 300,median*10):status='suspected_stall'
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/ps',timeout=3) as h:models=json.load(h)
        server='reachable'
    except Exception:server='unreachable'
    health=dict(observed_at=now,protocol='budget-pilot-v1',key=key,count_key=count,corpus=c,method=method,stage=stage,n=n,total=q.get('total'),classification=status,process_matches=child_alive,supervisor_alive=supervisor_alive,completed_calls=calls,last_confirmed_progress_at=last,no_progress_seconds=idle,median_seconds=median,ollama=server,deadline=entry.get('deadline'),corpus_outcomes={k:v.get('status') for k,v in sup.get('corpora',{}).items()})
    tmp=MON/'health.tmp';tmp.write_text(json.dumps(health,indent=2)+'\n');tmp.replace(MON/'health.json')
    with (MON/'observations.jsonl').open('a') as h:h.write(json.dumps(health)+'\n')
    print(json.dumps(health))
if __name__=='__main__':main()
