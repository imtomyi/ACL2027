"""All offline methods evaluate the exact same 100 IDs as the online stream."""
from pathlib import Path
import fcntl,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];CORPUS=os.environ['PILOT_CORPUS'];SUPERVISED=CORPUS in ('dreaddit','goemotions')
RUN=ROOT/'Storage/offline100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/CORPUS;OLD=ROOT/'Storage/budget_pilot/run_20260913'/CORPUS;ONLINE=ROOT/'Storage/online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/CORPUS;N=100
source=ROOT/'experiments/budget_pilot'/('supervised.py' if SUPERVISED else 'paired.py')
spec=importlib.util.spec_from_file_location('offline100_core',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.RUN=RUN;m.N=N;m.METHODS=['base','icl','miprov2','gepa'] if SUPERVISED else ['base','ace_offline_no_gt']
if SUPERVISED:m.NAMES=['Qwen3-8B','ICL','MIPROv2','GEPA']
else:m.g.RUN=RUN;m.g.METHODS=m.METHODS

def read(p):return json.loads(p.read_text()) if p.exists() else {}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,v):
    temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(v,indent=2)+'\n');temp.replace(p)
def jsonl(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def render():subprocess.run([sys.executable,str(ROOT/'experiments/reporting/update_results.py')],check=True,stdout=subprocess.DEVNULL)
m.render=render
if not SUPERVISED:m.g.render=render

def prepare():
    RUN.mkdir(parents=True,exist_ok=True);data=RUN/'data';data.mkdir(exist_ok=True)
    selected=jsonl(ONLINE/'data/test.jsonl');assert len(selected)==N
    if SUPERVISED:
        datasets,inventory=m.data();assert datasets['test']==selected
        original_freeze=m.freeze;m.freeze(datasets,inventory)
    else:
        for name,origin in [(CORPUS+'_test.jsonl',ONLINE/'data/test.jsonl'),(CORPUS+'_adapt.jsonl',OLD/'data'/f'{CORPUS}_adapt.jsonl')]:
            dest=data/name
            if dest.exists():assert dest.read_bytes()==origin.read_bytes()
            else:shutil.copy2(origin,dest)
        adapt=jsonl(data/f'{CORPUS}_adapt.jsonl');assert len(adapt)==4
        assert not ({r['source_id'] for r in adapt}&{r['source_id'] for r in selected})
        manifest={p.name:sha(p) for p in data.glob('*.jsonl')}
        if (data/'manifest.json').exists():assert read(data/'manifest.json')==manifest
        else:atomic(data/'manifest.json',manifest)
        # Copy the unchanged method specification, with this new run's actual scope and denominator.
        cfg=read(OLD/'frozen_config.json');assert cfg['methods']==m.METHODS
        cfg.update(protocol='offline100-v1',n=N,data_manifest=sha(data/'manifest.json'),teacher=None,
            gt_note='No GT or reference annotations; Acc and reference agreement N/A',
            protocols=dict(offline='4 adaptation examples; freeze memory; evaluate same 100 IDs as online',online='not in this queue',metrics='Acc N/A; final Conformability requires all 100 judgments and zero unresolved',limitations='GT-free local task transfer; same-family grounding judge; not exact paper reproduction'))
        cfg['code'][str(Path(__file__).resolve())]=sha(Path(__file__))
        if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform':
            from uniform_protocol import freeze_config
            cfg=freeze_config(cfg)
        if (RUN/'frozen_config.json').exists():assert read(RUN/'frozen_config.json')==cfg
        else:atomic(RUN/'frozen_config.json',cfg)
        for path,digest in cfg['code'].items():assert sha(Path(path))==digest
    contract=dict(protocol='offline100-v1',n=N,methods=m.METHODS,ordered_ids=[r['record_id'] for r in selected],online_data_sha256=sha(ONLINE/'data/test.jsonl'),wrapper_sha256=sha(Path(__file__)),task=m.TASK if SUPERVISED else m.g.TASK,
        counts='100 unique evaluation items per dataset, 400 total across four datasets. All methods reuse those IDs; training/demo/adaptation pools are separate.',
        import_policy=('Fresh uniform run: data only; no earlier outputs, caches, compiled optimizers or memory imported.' if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform' else 'Reuse only matching per-record outputs and unchanged offline adaptation state; never import aggregate scores as if denominators matched.'))
    if (RUN/'evaluation_contract.json').exists():assert read(RUN/'evaluation_contract.json')==contract
    else:atomic(RUN/'evaluation_contract.json',contract)
    shutil.copy2(Path(__file__),RUN/'offline100_implementation.py')
    if not (RUN/'reuse_manifest.json').exists():
        if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform':
            atomic(RUN/'reuse_manifest.json',dict(methods={},reason='Fresh uniform comparison; source data only, no earlier inference or memory reused.'))
        else:reuse(selected)
    render()

def reuse(selected):
    """Save computation only when exact prefix IDs, targets and frozen method settings agree."""
    evidence={};oldcfg=read(OLD/'frozen_config.json');newcfg=read(RUN/'frozen_config.json')
    for key in ['task','methods','model','seed','context','caps']:
        assert oldcfg[key]==newcfg[key],key
    if SUPERVISED:
        datasets,_=m.data()
        for split in ['train','dev']:assert oldcfg['selected_ids'][split]==[r['record_id'] for r in datasets[split]]
        for method in m.METHODS:
            old=OLD/method;dest=RUN/method;dest.mkdir(exist_ok=True)
            records=jsonl(old/'predictions.jsonl')[:N]
            assert [r['record_id'] for r in records]==[r['record_id'] for r in selected[:len(records)]]
            assert all(a['target']==b['target'] for a,b in zip(records,selected))
            if records:
                (dest/'predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
                atomic(dest/'state.json',dict(n=len(records),status='complete' if len(records)==N else 'running',scores=m.score(records)))
            quality=jsonl(old/'quality.jsonl')[:len(records)]
            assert [q['record_id'] for q in quality]==[r['record_id'] for r in records[:len(quality)]]
            assert all(q['answer_sha256']==hashlib.sha256(r['response'].encode()).hexdigest() for q,r in zip(quality,records))
            if quality:(dest/'quality.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in quality))
            copied=[]
            for name in ['response_cache','compiled.json','demonstrations.json']:
                origin=old/name
                if origin.is_dir():shutil.copytree(origin,dest/name);copied.append(name)
                elif origin.is_file():shutil.copy2(origin,dest/name);copied.append(name)
            evidence[method]=dict(source=str(old),predictions=len(records),judgments=len(quality),artifacts=copied,optimizer_search_state_resumed=False)
    else:
        oldrows=jsonl(OLD/'data'/f'{CORPUS}_test.jsonl');assert oldrows==selected[:len(oldrows)]
        assert sha(OLD/'data'/f'{CORPUS}_adapt.jsonl')==sha(RUN/'data'/f'{CORPUS}_adapt.jsonl')
        for method in m.METHODS:
            old=OLD/CORPUS/method;dest=RUN/CORPUS/method;dest.parent.mkdir(parents=True,exist_ok=True)
            if not old.exists():continue
            state=read(old/'state.json');n=state.get('n',0);assert n<=len(oldrows)
            for i in range(n):assert read(old/f'prediction_{i:04d}.json')['record_id']==selected[i]['record_id']
            quality=jsonl(old/'quality.jsonl');assert [q['record_id'] for q in quality]==[r['record_id'] for r in selected[:len(quality)]]
            shutil.copytree(old,dest);state.update(status='running' if n<N else 'complete');atomic(dest/'state.json',state)
            qs=read(dest/'quality_state.json')
            if qs:qs.update(total=N,status='running' if len(quality)<N else 'complete');atomic(dest/'quality_state.json',qs)
            evidence[method]=dict(source=str(old),predictions=n,judgments=len(quality),adapted=state.get('adapted',0),frozen_playbook_reused=True)
    atomic(RUN/'reuse_manifest.json',dict(at=time.time(),methods=evidence,reason='User corrected evaluation scope to 100 shared IDs per dataset; compatible individual records retained, final scores recomputed at N=100.'))

def run_topic(method):
    g=m.g;d=RUN/CORPUS/method;d.mkdir(parents=True,exist_ok=True);native=m.Native(d)
    state=read(d/'state.json') or dict(n=0,adapted=0,memory=g.EMPTY,next_id=1,status='running',recent_seconds=[])
    if method=='ace_offline_no_gt':
        adaptation=jsonl(RUN/'data'/f'{CORPUS}_adapt.jsonl')
        for i,row in enumerate(adaptation[state['adapted']:],state['adapted']):
            g.checkpoint(CORPUS,method,'adaptation',i,4);start=time.time();q=g.question(CORPUS,row)
            response,value=g.generate(native,q,state['memory'])
            state['memory'],state['next_id'],status=m.adapt(native,q,value,state['memory'],state['next_id'],i+1,4,None)
            g.atomic(d/f'adaptation_{i:04d}.json',dict(record_id=row['record_id'],update_status=status,reference_provided=False,seconds=time.time()-start))
            state.update(adapted=i+1,updated_at=time.time());atomic(d/'state.json',state);render()
    data=jsonl(RUN/'data'/f'{CORPUS}_test.jsonl')
    for i,row in enumerate(data[state['n']:],state['n']):
        g.checkpoint(CORPUS,method,'prediction',i,N);start=time.time();q=g.question(CORPUS,row)
        response,value=g.generate(native,q,g.EMPTY if method=='base' else state['memory'])
        try:pred=m.labels(json.loads(response).get('selected_topics'),CORPUS)
        except (ValueError,AttributeError):pred=None
        item=dict(record_id=row['record_id'],response=response,predicted_topics=pred,memory_before_sha256=hashlib.sha256(state['memory'].encode()).hexdigest())
        output=d/f'prediction_{i:04d}.json'
        if output.exists():assert read(output)==item
        else:atomic(output,item)
        state.update(n=i+1,status='complete' if i+1==N else 'running',updated_at=time.time(),recent_seconds=(state['recent_seconds']+[time.time()-start])[-20:])
        atomic(d/'state.json',state);g.checkpoint(CORPUS,method,'prediction',i+1,N);render()

def main():
    os.umask(0o077);RUN.mkdir(parents=True,exist_ok=True)
    if '--prepare-only' in sys.argv:prepare();return
    lock=(RUN/'queue.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        prepare()
        if SUPERVISED:
            data,_=m.data()
            for method in m.METHODS:m.evaluate(method,data)
            for method in m.METHODS:m.audit(method,data)
        else:
            for method in m.METHODS:run_topic(method);m.audit(CORPUS,method)
        atomic(RUN/'queue.json',dict(status='complete',updated_at=time.time()));render()
    except BaseException as exc:
        q=read(RUN/'queue.json');q.update(status='paused' if isinstance(exc,KeyboardInterrupt) else 'failed',error=type(exc).__name__,updated_at=time.time());atomic(RUN/'queue.json',q);render();raise
if __name__=='__main__':main()
