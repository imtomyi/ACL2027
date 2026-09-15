"""Own isolated localhost GPU services; no access to historical/shared services."""
from pathlib import Path
import argparse,json,os,socket,subprocess,time,urllib.request
from core import atomic,load

def identity(pid):
    try:
        stat=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
        return stat[19]
    except (FileNotFoundError,ProcessLookupError):return None

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();os.umask(0o077)
    root=a.root;runtime=load(root/'runtime.json');owner=root/'services';owner.mkdir(parents=True,exist_ok=True)
    gpus=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
    gpu={int(x[0]):x for x in [line.split(', ') for line in gpus.splitlines()]}
    existing=load(owner/'ownership.json') if (owner/'ownership.json').exists() else {'services':[]}
    records=existing['services']; skipped=[]
    for i in range(8):
        previous=next((r for r in records if r['gpu']==i and identity(r['pid'])==r['start_identity']),None)
        if previous:continue
        if int(gpu[i][2])>128 or int(gpu[i][3])!=0:
            skipped.append(i);continue
        port=11840+i;s=socket.socket()
        try:s.bind(('127.0.0.1',port))
        finally:s.close()
        env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu[i][1],OLLAMA_HOST=f'127.0.0.1:{port}',OLLAMA_MODELS=runtime['model_store'],OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_CONTEXT_LENGTH='32768',OLLAMA_FLASH_ATTENTION='1',OLLAMA_KEEP_ALIVE='30m')
        with (owner/f'gpu_{i}.log').open('ab') as log:
            proc=subprocess.Popen([runtime['ollama'],'serve'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        start=identity(proc.pid)
        if start is None:raise RuntimeError('Service did not survive startup')
        records.append({'gpu':i,'uuid':gpu[i][1],'port':port,'pid':proc.pid,'start_identity':start,'root':str(root),'started_at':time.time()})
        atomic(owner/'ownership.json',{'services':records,'profile':'a6000-8gpu-independent-runs-v1'})
    health=[]
    for r in records:
        for attempt in range(20):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{r["port"]}/api/tags',timeout=2) as f:models=json.load(f)['models']
                model=next(x for x in models if x['name']=='qwen3:8b')
                assert model['digest']==runtime['model_digest']
                assert model['details']['quantization_level']=='Q4_K_M'
                health.append({'gpu':r['gpu'],'port':r['port'],'model_digest_verified':True});break
            except (OSError,StopIteration):
                if attempt==19:raise
                time.sleep(.5)
    atomic(owner/'health.json',{'services':health,'skipped_busy_gpus':skipped,'model_calls':0});print(json.dumps({'healthy_services':len(health),'skipped_busy_gpus':skipped,'model_calls':0}))
if __name__=='__main__':main()
