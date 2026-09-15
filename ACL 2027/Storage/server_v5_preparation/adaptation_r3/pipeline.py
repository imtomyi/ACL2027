from pathlib import Path
import fcntl,json,os,subprocess,time
root=Path('/home/sy23985/Storage/acl2027_server_v5_20260914')
stage=root/'stages/adaptation_r3'
py='/home/sy23985/Storage/acl2027_miata_resume_20260913/runtime/venv/bin/python'
os.umask(0o077)
env=dict(os.environ,PYTHONPATH=str(stage/'code')+os.pathsep+str(root/'code'),PYTHONDONTWRITEBYTECODE='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
def write(status,**extra):
    value=dict(status=status,at=time.time(),active_stage='adaptation_r3',predecessor='adaptation_r2',do_not_resume_predecessor=True,**extra)
    for path in [stage/'pipeline_status.json',root/'ACTIVE_ADAPTATION_STAGE.json']:
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def identity(pid):
    try:
        f=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
        return None if f[0]=='Z' else f[19]
    except FileNotFoundError:return None
try:
    write('waiting_for_predecessor_checkpoint')
    deadline=time.monotonic()+2100
    while True:
        if (root/'STOP').exists() or (stage/'STOP').exists():raise RuntimeError('Stop requested')
        lock=(root/'prediction_controller.lock').open('a')
        ready=True
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:ready=False
        live=[]
        for path in (root/'stages').glob('*/runs/*/worker.json'):
            v=json.loads(path.read_text())
            if identity(v['pid'])==v['start_identity']:live.append(path.parent.name)
        lock.close()
        if ready and not live:break
        if time.monotonic()>deadline:raise RuntimeError('Predecessor did not drain within 35 minutes')
        time.sleep(3)
    for action in ['preflight','seal','launch']:
        write(action)
        subprocess.run([py,str(stage/'code/stage.py'),action,'--stage',str(stage)],env=env,check=True)
        if action=='preflight':
            v=json.loads((stage/'preflight/report.json').read_text())
            if v['passed']!=18:raise RuntimeError('Development preflight failed; production remains unadmitted')
        if action=='seal':
            (root/'stages/adaptation_r2/SUPERSEDED_BY.json').write_text(json.dumps(dict(stage=str(stage),at=time.time(),scope='ACE/DC; historical r1 artifacts preserved'))+'\n')
    write('controller_finished')
except BaseException as exc:
    write('pipeline_stopped',error_type=type(exc).__name__)
    raise
