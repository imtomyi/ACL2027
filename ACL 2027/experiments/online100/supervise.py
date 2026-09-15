"""Single-worker phase scheduler; adopts the active offline child without restarting it."""
from pathlib import Path
import fcntl,json,os,signal,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'Storage/budget_pilot'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913');ONLINE=ROOT/'Storage/online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913');OFFLINE=ROOT/'Storage/offline100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')
CORPORA=['cache','parlamint_gb','goemotions','dreaddit']
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
    # Completion priority is enabled only by recorded user authorization.
    if policy.get(phase+'_priority')=='complete_100':return None
    return entry['deadline']
def pause_for_storage(state,entry,phase_state,path,child_pid=None):
    free=shutil.disk_usage(ROOT).free
    if free>=1024**3:return False
    now=time.time()
    state.update(status='paused',pause_reason='low_disk_space',updated_at=now,
                 free_bytes_at_pause=free,recovery_minimum_free_bytes=3*1024**3)
    entry['status']='paused';phase_state['status']='paused'
    atomic(path,state)
    if child_pid:terminate(child_pid)
    action=dict(kind='preventive_storage_pause',at=now,corpus=state.get('corpus'),
                worker_pid=child_pid,free_bytes=free,reason='Below 1 GiB; preserve checkpoints before ENOSPC')
    with (ROOT/'Storage/experiment_monitor/actions.jsonl').open('a') as h:h.write(json.dumps(action)+'\n')
    atomic(path,state);render()
    return True

def main():
    lock=(RUN/'supervisor.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=RUN/'supervisor.json';state=read(path);state.update(status='running',pid=os.getpid(),script=str(Path(__file__).resolve()))
    atomic(path,state);child_pid=None
    try:
        for corpus in read(ONLINE/'policy.json').get('corpus_order',CORPORA):
            entry=state['corpora'].setdefault(corpus,{})
            if entry.get('remaining_budget_seconds') is not None and not entry.get('priority_resumed_at'):
                entry['deadline']=time.time()+entry['remaining_budget_seconds']
                entry['priority_resumed_at']=time.time()
            entry.setdefault('started_at',time.time());entry.setdefault('deadline',entry['started_at']+7200)
            phases=entry.setdefault('phases',{})
            for phase in (['online','offline'] if corpus=='cache' else ['offline','online']):
                phase_state=phases.setdefault(phase,{})
                if phase_state.get('status') in ('complete','failed','budget_exhausted'):continue
                limit=deadline(entry,phase)
                if limit is not None and time.time()>=limit:
                    phase_state.update(status='budget_exhausted',finished_at=time.time());entry['status']='budget_exhausted';atomic(path,state);render();continue
                directory=OFFLINE/corpus if phase=='offline' else ONLINE/corpus
                script=ROOT/'experiments'/('offline100' if phase=='offline' else 'online100')/'run.py'
                if read(ONLINE/'policy.json').get('uniform_policy'):
                    script=ROOT/'experiments/online100/run_uniform.py'
                recovery=read(ONLINE/'policy.json').get('output_cap_recovery')
                if recovery and f'{corpus}/{phase}' in recovery['scopes']:
                    script=ROOT/'experiments/online100/recover_output_limits.py'
                proc=None
                # Only an explicitly recorded handoff may adopt a live process.
                if entry.get('phase')==phase and phase_state.get('status')=='running' and alive(entry.get('pid')):
                    child_pid=entry['pid'];script=Path(entry['script'])
                    command=subprocess.check_output(['ps','-p',str(child_pid),'-o','command='],text=True)
                    assert str(script) in command,'Active worker identity mismatch'
                    phase_state['adopted_without_restart']=True
                else:
                    state['corpus']=corpus
                    entry.update(phase=phase,run_directory=str(directory))
                    if pause_for_storage(state,entry,phase_state,path):return
                    directory.mkdir(parents=True,exist_ok=True)
                    with (directory/'run.log').open('a') as log:
                        proc=subprocess.Popen([sys.executable,str(script)],env=dict(os.environ,PILOT_CORPUS=corpus,RECOVERY_PHASE=phase,PYTHONUNBUFFERED='1'),stdout=log,stderr=subprocess.STDOUT)
                    child_pid=proc.pid
                phase_state.update(status='running',pid=child_pid,script=str(script));phase_state.setdefault('started_at',time.time())
                entry.update(status='running',phase=phase,pid=child_pid,script=str(script),run_directory=str(directory))
                state.update(corpus=corpus,updated_at=time.time());atomic(path,state);render()
                while alive(child_pid) if proc is None else proc.poll() is None:
                    if pause_for_storage(state,entry,phase_state,path,child_pid):
                        child_pid=None
                        return
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
