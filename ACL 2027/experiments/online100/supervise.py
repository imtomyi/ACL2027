"""Single-worker phase scheduler; adopts the active offline child without restarting it."""
from pathlib import Path
import fcntl,json,os,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'Storage/budget_pilot/run_20260913';ONLINE=ROOT/'Storage/online100/run_20260913'
CORPORA=['goemotions','dreaddit','cache','parlamint_gb']
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def atomic(p,d):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def render():subprocess.run([sys.executable,str(ROOT/'experiments/reporting/update_results.py')],check=True,stdout=subprocess.DEVNULL)
def alive(pid):
    if not pid:return False
    r=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True)
    return r.returncode==0 and not r.stdout.strip().startswith('Z')
def terminate(pid):
    if not alive(pid):return
    os.kill(pid,signal.SIGINT)
    end=time.time()+45
    while alive(pid) and time.time()<end:time.sleep(1)
    if alive(pid):
        os.kill(pid,signal.SIGTERM);end=time.time()+10
        while alive(pid) and time.time()<end:time.sleep(1)
    if alive(pid):os.kill(pid,signal.SIGKILL)
def deadline(entry,phase):
    policy=read(ONLINE/'policy.json')
    # The outstanding time-budget question does not authorize extending the old cap.
    if phase=='online' and policy.get('online_priority')=='complete_100':return None
    return entry['deadline']
def main():
    lock=(RUN/'supervisor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=RUN/'supervisor.json';state=read(path);state.update(status='running',pid=os.getpid(),script=str(Path(__file__).resolve()))
    atomic(path,state);child_pid=None
    try:
        for corpus in CORPORA:
            entry=state['corpora'].setdefault(corpus,{})
            entry.setdefault('started_at',time.time());entry.setdefault('deadline',entry['started_at']+7200)
            phases=entry.setdefault('phases',{})
            for phase in ['offline','online']:
                phase_state=phases.setdefault(phase,{})
                if phase_state.get('status') in ('complete','failed','budget_exhausted'):continue
                limit=deadline(entry,phase)
                if limit is not None and time.time()>=limit:
                    phase_state.update(status='budget_exhausted',finished_at=time.time());entry['status']='budget_exhausted';atomic(path,state);render();continue
                directory=RUN/corpus if phase=='offline' else ONLINE/corpus
                script=ROOT/'experiments/online100'/('offline.py' if phase=='offline' else 'run.py')
                proc=None
                # Only an explicitly recorded handoff may adopt a live process.
                adopt=read(ONLINE/'handoff.json')
                if phase=='offline' and corpus==adopt.get('corpus') and not phase_state.get('started_at') and alive(adopt.get('child_pid')):
                    child_pid=adopt['child_pid'];script=Path(adopt['child_script']);phase_state['adopted']=True
                else:
                    directory.mkdir(parents=True,exist_ok=True)
                    with (directory/'run.log').open('a') as log:
                        proc=subprocess.Popen([sys.executable,str(script)],env=dict(os.environ,PILOT_CORPUS=corpus,PYTHONUNBUFFERED='1'),stdout=log,stderr=subprocess.STDOUT)
                    child_pid=proc.pid
                phase_state.update(status='running',pid=child_pid,script=str(script));phase_state.setdefault('started_at',time.time())
                entry.update(status='running',phase=phase,pid=child_pid,script=str(script),run_directory=str(directory))
                state.update(corpus=corpus,updated_at=time.time());atomic(path,state);render()
                while alive(child_pid) if proc is None else proc.poll() is None:
                    limit=deadline(entry,phase)
                    if limit is not None and time.time()>=limit:
                        terminate(child_pid);phase_state['status']='budget_exhausted';break
                    time.sleep(5)
                if proc:proc.wait()
                if phase_state['status']!='budget_exhausted':
                    phase_state['status']='complete' if read(directory/'queue.json').get('status')=='complete' else 'failed'
                phase_state['finished_at']=time.time();entry['status']=phase_state['status'];state['updated_at']=time.time();atomic(path,state);render();child_pid=None
            entry['status']='complete' if all(x.get('status')=='complete' for x in phases.values()) else 'budget_exhausted' if any(x.get('status')=='budget_exhausted' for x in phases.values()) else 'failed'
            atomic(path,state)
        state.update(status='finished',updated_at=time.time());atomic(path,state);render()
    except BaseException:
        if child_pid:terminate(child_pid)
        state.update(status='paused',updated_at=time.time());atomic(path,state);render();raise
if __name__=='__main__':main()
