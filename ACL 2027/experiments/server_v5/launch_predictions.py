"""One prediction worker per owned free GPU, durable queue, no judge calls."""
from pathlib import Path
import argparse,fcntl,json,os,subprocess,time
from core import atomic,load
from predict_stage import verify

def start_identity(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
    except FileNotFoundError:return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;os.umask(0o077)
    lock=(root/'prediction_controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    m=verify(root);ownership=load(root/'services/ownership.json')['services']
    for server in ownership:
        assert start_identity(server['pid'])==server['start_identity'],'GPU service ownership changed'
    slots=[x['gpu'] for x in ownership];active={};finished={};cells=list(m['cells']);last_report=0
    from report_predictions import report
    for cell in cells:
        d=root/'runs'/cell['id'];d.mkdir(parents=True,exist_ok=True)
        if (d/'state.json').exists() and load(d/'state.json')['status'].startswith('prediction_complete'):finished[cell['id']]='existing_complete'
        elif (d/'worker.json').exists():
            prior=load(d/'worker.json')
            if start_identity(prior['pid'])==prior['start_identity']:raise RuntimeError('A previous owned worker still runs; recover it before restarting controller')
    queue=[c for c in cells if c['id'] not in finished]
    while queue or active:
        stop=(root/'STOP').exists()
        for slot in slots:
            if stop or not queue or slot in active:continue
            # Services belong to this run; refuse a slot with foreign compute processes.
            listing=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
            uuid=next(s['uuid'] for s in ownership if s['gpu']==slot)
            foreign=False
            for line in listing.splitlines():
                parts=[x.strip() for x in line.split(',')]
                if len(parts)!=2 or parts[0]!=uuid:continue
                pid=int(parts[1]);env=Path(f'/proc/{pid}/environ')
                try:content=env.read_bytes()
                except (PermissionError,FileNotFoundError):foreign=True;continue
                if f'OLLAMA_HOST=127.0.0.1:{11840+slot}'.encode() not in content:foreign=True
            if foreign:continue
            cell=queue.pop(0);d=root/'runs'/cell['id']
            env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',PYTHONDONTWRITEBYTECODE='1')
            with (d/'worker.log').open('ab') as log:
                proc=subprocess.Popen([m['runtime']['python'],str(root/'code/predict_stage.py'),'--root',str(root),'--cell',cell['id'],'--gpu',str(slot)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            atomic(d/'worker.json',{'pid':proc.pid,'start_identity':start_identity(proc.pid),'gpu':slot,'started_at':time.time()});active[slot]=(proc,cell)
        for slot,(proc,cell) in list(active.items()):
            code=proc.poll()
            if code is not None:finished[cell['id']]='complete' if code==0 else 'failed';del active[slot]
        atomic(root/'prediction_queue.json',{'scope':'Base and ICL prediction stage','total_runs':len(cells),'queued':len(queue),'active':{str(g):c['id'] for g,(p,c) in active.items()},'finished':finished,'stop_requested':stop,'updated_at':time.time(),'status':'running' if active or queue and not stop else 'paused' if stop else 'complete'})
        if time.monotonic()-last_report>20 or not active:
            report(root);last_report=time.monotonic()
        if stop and not active:break
        time.sleep(3)
    report(root)
if __name__=='__main__':main()
