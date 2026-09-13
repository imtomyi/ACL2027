"""Serial, resumable four-corpus pilot with an explicit per-corpus wall-time cap."""
from pathlib import Path
import fcntl, hashlib, json, os, signal, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'Storage/budget_pilot/run_20260913'
CORPORA=['goemotions','dreaddit','cache','parlamint_gb']
BUDGET=7200

def atomic(p,d):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)

def render():
    subprocess.run([sys.executable,str(ROOT/'experiments/reporting/update_results.py')],stdout=subprocess.DEVNULL,check=True)

def main():
    os.umask(0o077);RUN.mkdir(parents=True,exist_ok=True)
    lock=(RUN/'supervisor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    p=RUN/'supervisor.json';s=json.loads(p.read_text()) if p.exists() else {'corpora':{}}
    s.update(status='running',pid=os.getpid(),updated_at=time.time());atomic(p,s)
    child=None
    try:
        for c in CORPORA:
            d=RUN/c;d.mkdir(exist_ok=True)
            entry=s['corpora'].setdefault(c,{})
            if entry.get('status') in ('complete','budget_exhausted','failed'):continue
            script=ROOT/'experiments/budget_pilot'/('supervised.py' if c in CORPORA[:2] else 'paired.py')
            now=time.time();entry.setdefault('started_at',now);entry.setdefault('deadline',now+BUDGET)
            if now>=entry['deadline']:
                entry.update(status='budget_exhausted',finished_at=now);atomic(p,s);continue
            env=dict(os.environ,PILOT_CORPUS=c,PYTHONUNBUFFERED='1')
            with (d/'run.log').open('a') as log:
                child=subprocess.Popen([sys.executable,str(script)],env=env,stdout=log,stderr=subprocess.STDOUT)
                entry.update(status='running',pid=child.pid,script=str(script));s.update(corpus=c,updated_at=time.time());atomic(p,s);render()
                while child.poll() is None:
                    if time.time()>=entry['deadline']:
                        child.send_signal(signal.SIGINT)
                        try:child.wait(timeout=45)
                        except subprocess.TimeoutExpired:
                            child.terminate()
                            try:child.wait(timeout=10)
                            except subprocess.TimeoutExpired:child.kill();child.wait()
                        entry['status']='budget_exhausted';break
                    time.sleep(5)
                entry.update(status=entry.get('status') if entry.get('status')=='budget_exhausted' else 'complete' if child.returncode==0 else 'failed',returncode=child.returncode,finished_at=time.time())
                s['updated_at']=time.time();atomic(p,s);render();child=None
        s.update(status='finished',updated_at=time.time());atomic(p,s);render()
    except BaseException:
        if child and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
        s.update(status='paused',updated_at=time.time());atomic(p,s);render();raise

if __name__=='__main__':main()
