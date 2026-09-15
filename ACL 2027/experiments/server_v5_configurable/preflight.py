"""Eight independent development probes; never writes evaluation scores."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,json,os,time,traceback
from core import Native,atomic,load,rows,question,output_schema,validate_output,evidence_checks

def probe(root,slot,job):
    corpus=['dreaddit','goemotions','cache','parlamint_gb'][job%4]
    row=rows(root/'data'/corpus/'dev.jsonl')[job//4]
    task=load(root/'tasks.json')[corpus];d=root/'preflight'/f'job_{job}_gpu_{slot}';d.mkdir(parents=True,exist_ok=True)
    previous=d/'status.json'
    if previous.exists() and load(previous).get('status')=='passed_output_schema':return load(previous)
    if previous.exists():atomic(d/'prior_failure.json',load(previous))
    params=load(root/'runtime.json');start=time.monotonic()
    report={'gpu':slot,'job':job,'dataset':corpus,'split':'dev','record_id':row['record_id'],'status':'running','evaluation_predictions':0,'started_at':time.time()}
    atomic(d/'status.json',report)
    try:
        n=Native(d/'calls',f'http://127.0.0.1:{11840+slot}',params['tokenizer'],42)
        schema=output_schema(task['labels'],task['single_label'])
        v=n.structured([{'role':'user','content':question(task,row)}],'prediction','development_probe',schema,lambda x:validate_output(x,task['labels'],task['single_label']))
        atomic(d/'output.json',v)
        report.update(status='passed_output_schema',seconds=time.monotonic()-start,evidence_checks=evidence_checks(v,row['text']))
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:300],seconds=time.monotonic()-start)
    atomic(d/'status.json',report)
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();os.umask(0o077)
    # Initialize Transformers lazy imports once before concurrent workers.
    from transformers import AutoTokenizer
    result=[]
    slots=[x['gpu'] for x in load(a.root/'services/health.json')['services']]
    if not slots:raise RuntimeError('No free owned GPU service')
    def worker(slot,jobs):
        reports=[]
        for job in jobs:
            report=probe(a.root,slot,job);reports.append(report)
            print(json.dumps({k:v for k,v in report.items() if k!='record_id'}),flush=True)
        return reports
    with ThreadPoolExecutor(max_workers=len(slots)) as pool:
        futures=[pool.submit(worker,slot,[j for j in range(8) if j%len(slots)==i]) for i,slot in enumerate(slots)]
        for future in as_completed(futures):
            result.extend(future.result())
            atomic(a.root/'preflight/status.json',{'scope':'development_only','finished':len(result),'total':8,'passed':sum(x['status']=='passed_output_schema' for x in result),'evaluation_predictions':0})
    atomic(a.root/'preflight/report.json',{'scope':'development_only_not_full_method_validation','probes':sorted(result,key=lambda r:r['gpu']),'evaluation_predictions':0,'status':'complete' if all(x['status']=='passed_output_schema' for x in result) else 'needs_repair'})
if __name__=='__main__':main()
