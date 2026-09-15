"""Ordered N=100 prequential DC/ACE transfer; distinct from offline pilots."""
from pathlib import Path
import contextlib, fcntl, hashlib, importlib.util, io, json, os, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2]
CORPUS=os.environ.get('PILOT_CORPUS','goemotions')
assert CORPUS in ('dreaddit','goemotions','cache','parlamint_gb')
SUPERVISED=CORPUS in ('dreaddit','goemotions')
RUN=ROOT/'Storage/online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/CORPUS
N=100
METHODS=['dc_online_ref','dc_online_no_gt','ace_online_ref','ace_online_no_gt'] if SUPERVISED else ['dc_online_no_gt','ace_online_no_gt']
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
# Reuse the pinned native adapters and ACE operations without changing active offline code.
os.environ['PILOT_CORPUS']='cache' if SUPERVISED else CORPUS
p=load('paired_online_core',ROOT/'experiments/budget_pilot/paired.py')
os.environ['PILOT_CORPUS']=CORPUS
g=p.g;p.RUN=g.RUN=RUN;p.CORPUS=CORPUS;p.METHODS=g.METHODS=METHODS
if SUPERVISED:
    s=load('classification_online_data',ROOT/'experiments/budget_pilot/supervised.py')
    s.N=N
    g.TOPICS={CORPUS:{str(i):label for i,label in enumerate(s.LABELS)}}
    g.TASK=s.TASK+' Return reasoning, bullet_ids (used playbook bullet IDs), final_answer (brief explanation), and selected_topics (the complete label set as string IDs). Use selected_topics as the sole machine-readable label field.'
    g.JUDGE=s.JUDGE_RUBRIC+' Label IDs in selected_topics are strings. Judge source grounding only; no reference label is supplied.'
else:
    s=None
p.OUTPUT_SCHEMA['properties']['selected_topics']['items']['enum']=list(g.TOPICS[CORPUS])
if CORPUS=='dreaddit':p.OUTPUT_SCHEMA['properties']['selected_topics']['maxItems']=1
g.GEN_SCHEMA=p.OUTPUT_SCHEMA

def read(path):return json.loads(path.read_text()) if path.exists() else {}
def rows():return g.read(RUN/'data/test.jsonl')
def feedback(reference):
    if SUPERVISED:
        return 'Released dataset labels for the CURRENT input, supplied only after its prediction was committed: '+json.dumps(reference['topic_ids'])+'. Use this feedback only to update memory for subsequent inputs.'
    return ORIGINAL_FEEDBACK(reference)
ORIGINAL_FEEDBACK=p.feedback;p.feedback=feedback

def prepare():
    RUN.mkdir(parents=True,exist_ok=True);data=RUN/'data';data.mkdir(exist_ok=True)
    if SUPERVISED:
        full,inventory=s.data();selected=full['test']
        provenance={'source_inventory':inventory,'selection':'SHA256 budget-pilot-v1:42:test:record_id; first 100 held-out test IDs'}
    else:
        source=ROOT/'Storage/paired_feedback/run_20260912/data'/f'{CORPUS}_test.jsonl'
        selected=sorted(g.read(source),key=lambda r:hashlib.sha256(('budget-pilot-v1:42:test:'+r['record_id']).encode()).hexdigest())[:N]
        provenance={'source':str(source),'source_sha256':g.sha(source),'selection':'SHA256 budget-pilot-v1:42:test:record_id; first 100 of preserved 200 held-out excerpts'}
    assert len(selected)==N and len({r['record_id'] for r in selected})==N
    raw=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected)
    target=data/'test.jsonl'
    if target.exists():assert target.read_text()==raw
    else:target.write_text(raw)
    manifest=dict(n=N,record_ids=[r['record_id'] for r in selected],sha256=g.sha(target),**provenance)
    if (data/'manifest.json').exists():assert read(data/'manifest.json')==manifest
    else:g.atomic(data/'manifest.json',manifest)
    files=[Path(__file__),ROOT/'experiments/budget_pilot/paired.py',p.CORE,g.SHARED/'comparison.py',g.SHARED/'optimizers.py',g.SHARED/'conformability.py',g.UPSTREAM/'playbook_utils.py',g.UPSTREAM/'utils.py']
    if SUPERVISED:files.append(ROOT/'experiments/budget_pilot/supervised.py')
    files+=list((g.UPSTREAM/'ace/prompts').glob('*.py'))
    dc_root=g.dc_adapter.__globals__['DC'];files+=list((dc_root/'dynamic_cheatsheet').rglob('*.py'))+list((dc_root/'prompts').glob('*.txt'))
    config=dict(protocol='online100-v1',corpus=CORPUS,n=N,methods=METHODS,model='qwen3:8b',quantization='Q4_K_M',seed=42,thinking=False,context=32768,
        task=g.TASK,codebook=g.TOPICS,output_schema=g.GEN_SCHEMA,judge=g.JUDGE,
        ground_truth='released dataset labels' if SUPERVISED else 'No reference labels generated or supplied; GT-free only; human Acc and reference agreement N/A',
        online='Empty initial memory per method. Same 100 IDs in fixed order. Commit prediction before feedback, update only future inputs. One pass. No offline playbook reuse. No judge feedback to adaptation.',
        caps=dict(generator=1024,dc_generator=2048,dc_curator=4096,reflector=1536,curator=2048,playbook=8000,judge=384,teacher=1024),
        limitations='Local task transfer, not exact paper reproduction. Same-family judge/reference bias. Small ordered stream. Sampling differs from full and offline pilots.',
        data_manifest=g.sha(data/'manifest.json'),code={str(f):g.sha(f) for f in files})
    if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform':
        from uniform_protocol import freeze_config
        config=freeze_config(config)
    if (RUN/'frozen_config.json').exists():assert read(RUN/'frozen_config.json')==config
    else:g.atomic(RUN/'frozen_config.json',config)
    for f in files:
        dest=RUN/'implementation_snapshot'/f.relative_to(ROOT.parent);dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert g.sha(dest)==g.sha(f)
        else:shutil.copy2(f,dest)
    render()

def prepare_references():
    if SUPERVISED or not any(m.endswith('_ref') for m in METHODS):return
    directory=RUN/'references';directory.mkdir(exist_ok=True);native=p.Native(directory/'calls')
    for i,row in enumerate(rows()):
        dest=directory/f'{i:04d}.json'
        if dest.exists():
            ref=read(dest);assert ref['record_id']==row['record_id'];assert ref['source_sha256']==hashlib.sha256(row['text'].encode()).hexdigest();p.validate_reference(ref,CORPUS,row);continue
        g.checkpoint(CORPUS,'reference_annotator','annotation',i,N);start=time.time()
        for attempt in range(3):
            try:
                raw=native.chat([dict(role='system',content=p.TEACHER),dict(role='user',content=json.dumps(dict(codebook=g.TOPICS[CORPUS],source=row['text'],technical_attempt=attempt+1)))],max_tokens=1024,role='reference_annotation',output_format=p.annotation_schema(CORPUS))
                value=json.loads(raw);value['topic_ids']=p.validate_reference(value,CORPUS,row);break
            except (ValueError,AssertionError,KeyError,TypeError):
                if attempt==2:raise
        value.update(record_id=row['record_id'],source_sha256=hashlib.sha256(row['text'].encode()).hexdigest(),seconds=time.time()-start,provenance='unverified local Qwen3-8B annotation')
        g.atomic(dest,value);g.checkpoint(CORPUS,'reference_annotator','annotation',i+1,N);render()
    seal={x.name:g.sha(x) for x in sorted(directory.glob('[0-9]*.json'))};assert len(seal)==N
    if (directory/'sealed.json').exists():assert read(directory/'sealed.json')==seal
    else:g.atomic(directory/'sealed.json',seal)

def reference(i,row):
    if SUPERVISED:return dict(topic_ids=sorted(map(str,row['target'])),record_id=row['record_id'])
    seal=read(RUN/'references/sealed.json');dest=RUN/'references'/f'{i:04d}.json';assert seal[dest.name]==g.sha(dest)
    result=read(dest);assert result['record_id']==row['record_id'];return result

def commit_prediction(path,item):
    if path.exists():assert read(path)==item
    else:g.atomic(path,item)

class Native(p.Native):
    pending_prediction=None
    def chat(self,messages,**kw):
        response=super().chat(messages,**kw)
        # DC calls its curator internally; durably save generator output before that call.
        if kw.get('role')=='prediction' and self.pending_prediction is not None:
            path,item=self.pending_prediction
            commit_prediction(path,dict(**item,response=response,predicted_topics=parse(response)))
        return response

def parse(response):
    try:value=p.labels(json.loads(response).get('selected_topics'),CORPUS)
    except (ValueError,AttributeError,TypeError):return None
    if CORPUS=='dreaddit' and value is not None and len(value)!=1:return None
    return value

def adapt(native,q,value,memory,next_id,step,ref):
    result=_adapt_impl(native,q,value,memory,next_id,step,ref)
    if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform':
        from uniform_protocol import bounded_memory
        candidate,accepted=bounded_memory(native,memory,result[0])
        if not accepted:return candidate,next_id,'retained_previous_over_budget'
    return result

def _adapt_impl(native,q,value,memory,next_id,step,ref):
    if ref is None:return g.adapt(native,q,value,memory,next_id,step,N)
    # Paired helper uses official GT templates and bullet operations; wording must reflect true GT provenance.
    if not SUPERVISED:return p.adapt(native,q,value,memory,next_id,step,N,ref)
    prompt=p.REF_GT.format(q,value['reasoning'],value['final_answer'],feedback(ref),'Released dataset labels are the evaluation reference; the current prediction has already been committed.',g.extract_playbook_bullets(memory,value['bullet_ids']))
    raw=native.chat([dict(role='user',content=prompt)],max_tokens=1536,role='reflector',output_format='json')
    try:
        parsed=json.loads(raw);tags=parsed.get('bullet_tags',[])
    except (ValueError,AttributeError):return memory,next_id,'retained_previous_invalid_reflection'
    tags=[t for t in tags if isinstance(t,dict) and isinstance(t.get('id'),str) and t.get('tag') in ('helpful','harmful','neutral')] if isinstance(tags,list) else []
    updated=g.update_bullet_counts(memory,tags)
    prompt=p.CUR_GT.format(current_step=step,total_samples=N,token_budget=(4096 if os.environ.get('EXPERIMENT_RUN_ID')=='run_20260914_uniform' else 8000),playbook_stats=json.dumps(g.get_playbook_stats(updated)),recent_reflection=raw,current_playbook=updated,question_context=q+'\n'+feedback(ref))
    raw=native.chat([dict(role='user',content=prompt)],max_tokens=2048,role='curator',output_format='json')
    try:
        ops=json.loads(raw)['operations'];assert isinstance(ops,list)
        assert all(isinstance(o,dict) and o.get('type')=='ADD' and isinstance(o.get('section'),str) and isinstance(o.get('content'),str) for o in ops)
        with contextlib.redirect_stdout(io.StringIO()):candidate,candidate_id=g.apply_curator_operations(updated,ops,next_id)
        if len(native.tokenizer.encode(candidate))>8000:return updated,next_id,'retained_previous_over_budget'
        return candidate,candidate_id,'accepted'
    except (ValueError,AssertionError,KeyError,TypeError):return updated,next_id,'retained_previous_invalid_operations'

def run_method(method):
    d=RUN/method;d.mkdir(exist_ok=True);native=Native(d);dc=g.dc_adapter(native) if method.startswith('dc_') else None
    state=read(d/'state.json') or dict(n=0,memory='(empty)' if dc else g.EMPTY,next_id=1,status='running',recent_seconds=[])
    has_ref=method.endswith('_ref')
    for i,row in enumerate(rows()[state['n']:],state['n']):
        g.checkpoint(CORPUS,method,'prediction',i,N);start=time.time();q=g.question(CORPUS,row)
        path=d/f'prediction_{i:04d}.json';identity=dict(record_id=row['record_id'],memory_before_sha256=hashlib.sha256(state['memory'].encode()).hexdigest())
        if dc:
            native.pending_prediction=(path,identity)
            native.reference=reference(i,row) if has_ref else None
            response,new_memory=dc(q,state['memory'],None)
            commit_prediction(path,dict(**identity,response=response,predicted_topics=parse(response)))
            native.reference=None;native.pending_prediction=None
            state['memory']=new_memory;update_status='see_dc_steps'
        else:
            response,value=g.generate(native,q,state['memory'])
            commit_prediction(path,dict(**identity,response=response,predicted_topics=parse(response)))
            state['memory'],state['next_id'],update_status=adapt(native,q,value,state['memory'],state['next_id'],i+1,reference(i,row) if has_ref else None)
        state.update(n=i+1,status='complete' if i+1==N else 'running',updated_at=time.time(),update_status=update_status,recent_seconds=(state['recent_seconds']+[time.time()-start])[-20:])
        g.atomic(d/'state.json',state);g.checkpoint(CORPUS,method,'prediction',i+1,N);render()

def audit(method):
    d=RUN/method;native=Native(d/'quality_calls');items=g.read(d/'quality.jsonl')
    for i,row in enumerate(rows()[len(items):],len(items)):
        g.checkpoint(CORPUS,method,'conformability',i,N);start=time.time();pred=read(d/f'prediction_{i:04d}.json');assert pred['record_id']==row['record_id']
        decision=value=None;error=None
        for attempt in range(3):
            try:
                value=json.loads(native.chat([dict(role='system',content=g.JUDGE+'\nCodebook: '+json.dumps(g.TOPICS[CORPUS])),dict(role='user',content=json.dumps(dict(source_passage=row['text'],anonymous_answer=pred['response'],technical_attempt=attempt+1)))],max_tokens=384,role='quality_judge',output_format=g.SCHEMA))
                decision=g.decide(value);error=None;break
            except Exception as exc:error=type(exc).__name__
        item=dict(record_id=row['record_id'],decision=decision,judgment=value,error=error,seconds=time.time()-start)
        g.append(d/'quality.jsonl',item);items.append(item)
        g.atomic(d/'quality_state.json',dict(n=len(items),total=N,passed=sum(x['decision'] is True for x in items),unresolved=sum(x['decision'] is None for x in items),recent_seconds=[x['seconds'] for x in items[-20:]]));render()

def render():
    # Shared reporter reads committed states only and never memory contents.
    subprocess.run([sys.executable,str(ROOT/'experiments/reporting/update_results.py')],check=True,stdout=subprocess.DEVNULL)

def main():
    os.umask(0o077);RUN.mkdir(parents=True,exist_ok=True)
    lock=(RUN/'queue.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        prepare()
        if '--prepare-only' in sys.argv:return
        prepare_references()
        for method in METHODS:run_method(method);audit(method)
        g.atomic(RUN/'queue.json',dict(status='complete',corpus=CORPUS,updated_at=time.time()));render()
    except BaseException as exc:
        state=read(RUN/'queue.json');state.update(status='paused' if isinstance(exc,KeyboardInterrupt) else 'failed',error=type(exc).__name__,updated_at=time.time());g.atomic(RUN/'queue.json',state);render();raise
if __name__=='__main__':main()
