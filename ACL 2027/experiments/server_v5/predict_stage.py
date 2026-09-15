"""Sealed Base/ICL prediction stage; judges and unimplemented adapters are separate."""
from pathlib import Path
import argparse,fcntl,hashlib,itertools,json,os,random,signal,sys,time
from core import Native,atomic,load,rows,question,output_schema,validate_output,evidence_checks,digest

def verify(root):
    m=load(root/'prediction_manifest.json')
    if m['seal_sha256']!=digest({k:v for k,v in m.items() if k!='seal_sha256'}):raise RuntimeError('Prediction manifest digest mismatch')
    for p,h in m['files'].items():
        if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Prediction-stage seal changed: '+p)
    return m

def literal_anchors(value,text):
    result=[]
    for e in value['evidence']:
        quote=e['quote'];positions=[];pos=0
        if quote:
            while True:
                pos=text.find(quote,pos)
                if pos<0:break
                positions.append(pos);pos+=1
        original_ok=e['start'] in positions and e['end']==e['start']+len(quote)
        selected=e['start'] if original_ok else positions[0] if len(positions)==1 else None
        result.append({'label_id':e['label_id'],'literal_match':bool(positions),'occurrences':len(positions),'reported_offset_valid':original_ok,'resolved_start':selected,'resolved_end':selected+len(quote) if selected is not None else None,'resolution':'model_offset' if original_ok else 'unique_exact_match' if selected is not None else 'unresolved','quote_sha256':hashlib.sha256(quote.encode()).hexdigest()})
    return result

def run(root,cell,gpu):
    os.umask(0o077);manifest=verify(root);task=load(root/'tasks.json')[cell['dataset']]
    d=root/'runs'/cell['id'];d.mkdir(parents=True,exist_ok=True)
    lock=(d/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    n=Native(d/'calls',f'http://127.0.0.1:{11840+gpu}',manifest['runtime']['tokenizer'],cell['seed'])
    test=rows(root/'data'/cell['dataset']/'test.jsonl')
    # Strip GT from the generator's records. Isolated scoring reads reference files later.
    sources={r['record_id']:{'record_id':r['record_id'],'text':r['text']} for r in test}
    order=load(root/'orders.json')[cell['dataset']][str(cell['seed'])]
    schema=output_schema(task['labels'],task['single_label'])
    demos=load(root/'demonstrations.json')[cell['dataset']][str(cell['seed'])] if cell['method']=='icl' else None
    started=time.time();base_elapsed=load(d/'state.json').get('active_seconds',0) if (d/'state.json').exists() else 0
    clock=time.monotonic()
    def status(kind,error=None):
        outputs=list(d.glob('prediction_*.json'));valid=sum(load(p).get('valid',False) for p in outputs)
        value={'condition_id':cell['id'],'dataset':cell['dataset'],'method':cell['method'],'seed':cell['seed'],'phase':cell['phase'],'adaptation_gt':cell['adaptation_gt'],'status':kind,'attempted':len(outputs),'predicted':valid,'total':100,'judged':0,'judge_status':'pending_selection','gpu':gpu,'pid':os.getpid(),'active_seconds':base_elapsed+time.monotonic()-clock,'updated_at':time.time(),'prediction_seal_sha256':manifest['seal_sha256']}
        if error:value['error_type']=error
        atomic(d/'state.json',value)
    try:
        status('running')
        for i,rid in enumerate(order):
            if (root/'STOP').exists():raise KeyboardInterrupt()
            p=d/f'prediction_{i:03d}.json'
            if p.exists():assert load(p)['record_id']==rid;continue
            source=sources[rid];messages=[]
            if demos:
                messages.append({'role':'system','content':'Use these fixed labeled demonstrations for the task. Follow the final response schema for the new source.\n'+demos['text']})
            messages.append({'role':'user','content':question(task,source)})
            t=time.monotonic()
            try:
                output=n.structured(messages,'prediction',f'evaluation:{i}:{rid}',schema,lambda x:validate_output(x,task['labels'],task['single_label']))
                value={'record_id':rid,'index':i,'valid':True,'output':output,'output_sha256':digest(output),'source_sha256':hashlib.sha256(source['text'].encode()).hexdigest(),'seconds':time.monotonic()-t,'reported_offset_checks':evidence_checks(output,source['text']),'literal_anchors':literal_anchors(output,source['text'])}
            except ValueError as exc:
                if str(exc)!='Format retries exhausted':raise
                value={'record_id':rid,'index':i,'valid':False,'output':None,'source_sha256':hashlib.sha256(source['text'].encode()).hexdigest(),'seconds':time.monotonic()-t,'error_type':'exhausted_format_failure'}
            atomic(p,value);status('running')
        status('prediction_complete' if all(load(p)['valid'] for p in d.glob('prediction_*.json')) else 'prediction_complete_with_failures')
    except BaseException as exc:
        status('paused' if isinstance(exc,KeyboardInterrupt) else 'failed',type(exc).__name__);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cell',required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
    m=verify(a.root);cell=next(x for x in m['cells'] if x['id']==a.cell);run(a.root,cell,a.gpu)
