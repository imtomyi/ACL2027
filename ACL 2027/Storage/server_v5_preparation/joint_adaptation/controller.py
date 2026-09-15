"""Operational dispatcher: preserved sealed r3 ACE + separately sealed r4 DC."""
from pathlib import Path
import fcntl,hashlib,json,os,subprocess,time
ROOT=Path('/home/sy23985/Storage/acl2027_server_v5_20260914')
PY='/home/sy23985/Storage/acl2027_miata_resume_20260913/runtime/venv/bin/python'
STAGES={name:ROOT/'stages'/name for name in ['adaptation_r3','adaptation_r4']}
CONTROL=ROOT/'joint_adaptation'
os.umask(0o077)
def load(p):return json.loads(p.read_text())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def atomic(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2)+'\n');tmp.replace(p)
def identity(pid):
 try:
  fields=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
  return fields[19] if fields[0]!='Z' else None
 except FileNotFoundError:return None

def main():
 atomic(CONTROL/'dispatch.json',dict(pid=os.getpid(),start_identity=identity(os.getpid()),started_at=time.time()))
 locks=[]
 for path in [ROOT/'prediction_controller.lock']+[d/'controller.lock' for d in STAGES.values()]:
  f=path.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
 manifests={name:load(d/'manifest.json') for name,d in STAGES.items()}
 for m in manifests.values():
  assert m['seal_sha256']==digest({k:v for k,v in m.items() if k!='seal_sha256'})
  for file,sha in m['files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==sha
 for path in ROOT.glob('stages/*/runs/*/worker.json'):
  v=load(path);assert identity(v['pid'])!=v['start_identity'],'Previous worker is live'
 for name,d in STAGES.items():
  dispatch=load(d/'dispatch.json')
  # r4's wrapper is our parent; r3's original controller/pipeline must have ended.
  if name=='adaptation_r3':assert identity(dispatch['pid'])!=dispatch['start_identity'],'Original r3 pipeline still alive'
 assert not (ROOT/'STOP').exists() and not (STAGES['adaptation_r4']/'STOP').exists()
 stop=STAGES['adaptation_r3']/'STOP'
 if stop.exists():
  reason=stop.read_text();assert reason.startswith('Operational pause for joint continuation')
  atomic(CONTROL/'REMOVED_OPERATIONAL_STOP.json',dict(path=str(stop),content=reason,at=time.time()))
  stop.unlink()
 owned=load(ROOT/'services/ownership.json')['services']
 for service in owned:assert identity(service['pid'])==service['start_identity']
 original=manifests['adaptation_r3']['admitted_cells'];new={c['id']:c for c in manifests['adaptation_r4']['admitted_cells']}
 jobs=[('adaptation_r3',c) if c['method']=='ace' else ('adaptation_r4',new[c['id']]) for c in original]
 assert len(jobs)==54 and sum(c['method']=='ace' for _,c in jobs)==36 and len(new)==18
 atomic(CONTROL/'MANIFEST.json',dict(stage_seals={k:m['seal_sha256'] for k,m in manifests.items()},
  controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  scope='36 existing r3 ACE trajectories resumed exactly; 18 fresh r4 DC trajectories. Original r3 DC trajectories superseded, never erased.',jobs=[dict(stage=n,cell=c) for n,c in jobs],at=time.time()))
 queue=[];finished={};active={};last_report=0
 for name,cell in jobs:
  d=STAGES[name]/'runs'/cell['id'];d.mkdir(parents=True,exist_ok=True)
  state=load(d/'state.json') if (d/'state.json').exists() else {}
  if state.get('status','').startswith('prediction_complete') or state.get('status')=='failed':finished[cell['id']]=dict(stage=name,status=state['status'])
  else:queue.append((name,cell))
 while queue or active:
  stop=(ROOT/'STOP').exists() or any((d/'STOP').exists() for d in STAGES.values())
  listing=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
  for service in owned:
   gpu=service['gpu']
   if stop or not queue or gpu in active:continue
   assert identity(service['pid'])==service['start_identity']
   foreign=False
   for line in listing.splitlines():
    bits=[x.strip() for x in line.split(',')]
    if len(bits)!=2 or bits[0]!=service['uuid']:continue
    try:env_bytes=Path(f'/proc/{int(bits[1])}/environ').read_bytes().split(b'\0')
    except FileNotFoundError:continue
    except PermissionError:foreign=True;continue
    if f'OLLAMA_HOST=127.0.0.1:{11840+gpu}'.encode() not in env_bytes:foreign=True
   if foreign:continue
   name,cell=queue.pop(0);stage=STAGES[name];d=stage/'runs'/cell['id']
   env=dict(os.environ,PYTHONPATH=str(stage/'code')+os.pathsep+str(ROOT/'code'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1')
   with (d/'worker.log').open('ab') as log:
    p=subprocess.Popen([PY,str(stage/'code/run.py'),'--stage',str(stage),'--cell',cell['id'],'--gpu',str(gpu)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
   atomic(d/'worker.json',dict(pid=p.pid,start_identity=identity(p.pid),gpu=gpu,started_at=time.time(),controller=str(CONTROL)))
   active[gpu]=(p,name,cell)
  for gpu,(p,name,cell) in list(active.items()):
   if p.poll() is not None:
    path=STAGES[name]/'runs'/cell['id']/'state.json';state=load(path) if path.exists() else {}
    finished[cell['id']]=dict(stage=name,status=state.get('status','worker_failed_before_state'));del active[gpu]
  status='running' if active or queue and not stop else 'paused' if stop else 'complete'
  atomic(CONTROL/'queue.json',dict(status=status,queued=len(queue),active={str(g):dict(stage=n,cell=c['id']) for g,(p,n,c) in active.items()},finished=finished,stop_requested=stop,updated_at=time.time()))
  atomic(ROOT/'ACTIVE_ADAPTATION_STAGE.json',dict(active_stage='adaptation_r4',continuing_ace_stage='adaptation_r3',status='joint_'+status,joint_controller=str(CONTROL),at=time.time()))
  for name,stage in STAGES.items():
   atomic(stage/'queue.json',dict(total_runs=36 if name=='adaptation_r3' else 18,queued=sum(n==name for n,c in queue),active={str(g):c['id'] for g,(p,n,c) in active.items() if n==name},finished={k:v['status'] for k,v in finished.items() if v['stage']==name},stop_requested=stop,status=status,updated_at=time.time(),controller=str(CONTROL)))
  if time.monotonic()-last_report>20 or not active:
   for stage in STAGES.values():
    env=dict(os.environ,PYTHONPATH=str(stage/'code')+os.pathsep+str(ROOT/'code'),PYTHONDONTWRITEBYTECODE='1')
    with (CONTROL/'reports.log').open('ab') as log:subprocess.run([PY,str(stage/'code/stage.py'),'report','--stage',str(stage)],env=env,stdout=log,stderr=log,check=True)
   last_report=time.monotonic()
  if stop and not active:break
  time.sleep(3)

if __name__=='__main__':main()
