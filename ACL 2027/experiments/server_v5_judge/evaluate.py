"""Separate, restartable evaluation of immutable prediction artifacts."""
from pathlib import Path
import argparse, concurrent.futures, fcntl, hashlib, json, os, subprocess, sys, time, urllib.request
from core import Native, atomic, load, rows, digest, validate_output
from rubric import VERSION, SYSTEM, SCHEMA, DIMENSIONS, validate, messages, decision


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
        return None if fields[0]=='Z' else fields[19]
    except FileNotFoundError:return None


def check_stop(parent, stage):
    if (parent/'STOP').exists() or (stage/'STOP').exists(): raise KeyboardInterrupt()


def verify_manifest(path, relative):
    manifest=load(path)
    if manifest['seal_sha256']!=digest({k:v for k,v in manifest.items() if k!='seal_sha256'}):raise RuntimeError('Manifest digest mismatch')
    for filename,checksum in manifest['files'].items():
        if sha(relative/filename)!=checksum:raise RuntimeError('Source seal changed')
    return manifest


def clean_services(services, listing, environ):
    # A GPU running another account's process is left untouched and excluded, never shared.
    by_uuid={s['uuid']:s for s in services};foreign=set()
    for line in listing.splitlines():
        parts=[v.strip() for v in line.split(',')]
        if len(parts)!=2 or parts[0] not in by_uuid:continue
        s=by_uuid[parts[0]]
        try:environment=environ(int(parts[1]))
        except FileNotFoundError:continue
        except PermissionError:foreign.add(parts[0]);continue
        if f'OLLAMA_HOST=127.0.0.1:{s["port"]}'.encode() not in environment:foreign.add(parts[0])
    return [s for s in services if s['uuid'] not in foreign],sorted(by_uuid[u]['gpu'] for u in foreign)


def owned_services(parent):
    services=load(parent/'services/ownership.json')['services']
    for s in services:
        if identity(s['pid'])!=s['start_identity']:raise RuntimeError('Owned service changed')
    for directory in [parent/'runs']+list((parent/'stages').glob('*/runs'))+list((parent/'evaluation').glob('*/runs')):
        for p in directory.glob('*/worker.json'):
            prior=load(p)
            if identity(prior['pid'])==prior['start_identity']:raise RuntimeError('Existing worker still live')
    listing=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
    clean,excluded=clean_services(services,listing,lambda pid:Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'))
    if not clean:raise RuntimeError('Every owned GPU runs a process outside ownership')
    OWNED_EXCLUDED[:]=excluded
    return clean


OWNED_EXCLUDED=[]


def judge_one(native, task, source, prediction, key):
    if prediction['source_sha256']!=hashlib.sha256(source.encode()).hexdigest():raise RuntimeError('Source binding mismatch')
    if not prediction['valid']:
        return dict(status='invalid_prediction',resolved=True,**{'pass':False},llm_judged=False,
                    dimensions=None,rationale=None)
    output=prediction['output']
    if prediction['output_sha256']!=digest(output):raise RuntimeError('Output binding mismatch')
    validate_output(output,task['labels'],task['single_label'])
    request=messages(task,source,output)
    try:
        result=native.structured(request,'judge',key,SCHEMA,validate)
    except ValueError as exc:
        if str(exc) not in ['Format retries exhausted','Length exhaustion; truncated response discarded']:raise
        return dict(status='unresolved_output_failure',resolved=False,**{'pass':None},llm_judged=False,
                    dimensions=None,rationale=None,error_type=str(exc),payload_sha256=digest(request))
    return dict(status='rated',llm_judged=True,**result,**decision(result,output),payload_sha256=digest(request))


def summarize(records,total):
    resolved=sum(v['resolved'] for v in records); passed=sum(v['pass'] is True for v in records)
    return dict(processed=len(records),llm_judged=sum(v['llm_judged'] for v in records),resolved=resolved,
        passes=passed,failures=resolved-passed,unresolved=total-resolved,
        invalid_predictions=sum(v['status']=='invalid_prediction' for v in records),
        conformability=100*passed/total if resolved==total else None,
        resolved_only_pass_rate=100*passed/resolved if resolved else None,
        full_panel_bounds=[100*passed/total,100*(passed+total-resolved)/total],
        dimension_means={k:sum(values)/len(values) if values else None for k in DIMENSIONS
                         for values in [[v['dimensions'][k] for v in records if v.get('dimensions') and v['dimensions'][k] is not None]]},
        dimension_n={k:sum(v.get('dimensions') is not None and v['dimensions'][k] is not None for v in records) for k in DIMENSIONS})


def cohort(stage):
    # A later frozen input cohort names its prediction stages; the first cohort keeps its fixed 72 runs.
    path=stage/'cohort.json'
    return load(path) if path.exists() else None


def inventory(parent, stage):
    selected={};spec=cohort(stage)
    sources=[(parent/s,'manifest.json',m) for s,m in spec['sources']] if spec else [(parent,'prediction_manifest.json',None),
            (parent/'stages/adaptation_r3','manifest.json','ace'),
            (parent/'stages/adaptation_r4','manifest.json','dc_cu'),
            (parent/'stages/adaptation_r5_retained','manifest.json','dc_cu')]
    for directory,filename,method in sources:
        manifest=verify_manifest(directory/filename,directory)
        for cell in manifest.get('admitted_cells',manifest['cells']):
            if method and cell['method']!=method:continue
            key=tuple(cell[k] for k in ['dataset','phase','method','adaptation_gt','seed'])
            selected[key]=(cell,directory,manifest)
    if len(selected)!=(spec['expected_runs'] if spec else 72):raise RuntimeError('Unexpected current prediction cohort')
    cells=[]
    for cell,directory,manifest in sorted(selected.values(),key=lambda v:v[0]['id']):
        d=directory/'runs'/cell['id'];state=load(d/'state.json')
        if state['status'] not in ['prediction_complete','prediction_complete_with_failures']:raise RuntimeError('Prediction cohort is not ready')
        if cell['method'] in ['ace','dc_cu'] and state.get('updated')!=100:raise RuntimeError('Incomplete adaptation')
        paths=sorted(d.glob('prediction_*.json'))
        if len(paths)!=100 or state['attempted']!=100:raise RuntimeError('Incomplete prediction panel')
        source_ids={r['record_id'] for r in rows(parent/'data'/cell['dataset']/'test.jsonl')}
        if {load(p)['record_id'] for p in paths}!=source_ids:raise RuntimeError('Evaluation IDs mismatch')
        cells.append(dict(cell=cell,source_stage='live' if directory==parent else directory.name,
            prediction_seal_sha256=manifest['seal_sha256'],
            predictions=[dict(path=str(p),sha256=sha(p),index=load(p)['index']) for p in paths]))
    return cells


def preflight(parent, stage, services, runtime):
    from transformers import AutoTokenizer  # Resolve lazy imports before threads.
    tasks=load(parent/'tasks.json');cases=[]
    for corpus in tasks:
        d=parent/'stages/adaptation_r3/preflight'/f'{corpus}__online__ace__gt_no__seed42'
        sources={r['record_id']:r['text'] for r in rows(parent/'data'/corpus/'dev.jsonl')}
        for p in sorted(d.glob('prediction_*.json'))[:2]:
            cases.append((corpus,p,sources[load(p)['record_id']]))
    if len(cases)!=8:raise RuntimeError('Development-only judge cases unavailable')
    def run(item):
        i,(corpus,p,source)=item;s=services[i%len(services)]
        native=Native(stage/'preflight'/str(i)/'calls',f'http://127.0.0.1:{s["port"]}',runtime['tokenizer'],42)
        result=judge_one(native,tasks[corpus],source,load(p),'development:'+sha(p))
        atomic(stage/'preflight'/str(i)/'judgment.json',result)
        return dict(dataset=corpus,prediction_sha256=sha(p),llm_judged=result['llm_judged'],
                    all_dimensions_assessable=bool(result.get('dimensions')) and all(v is not None for v in result['dimensions'].values()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(run,enumerate(cases)))
    passed=all(v['llm_judged'] and v['all_dimensions_assessable'] for v in results)
    atomic(stage/'preflight/report.json',dict(passed=passed,cases=results,n=8,
        gate='Format and assessability only; pass/fail quality scores do not select the rubric.',
        human_calibration='not_collected',at=time.time()))
    if not passed:raise RuntimeError('Judge development format gate failed')


def seal(parent, stage, services):
    if (stage/'manifest.json').exists():return verify_manifest(stage/'manifest.json',stage)
    runtime=load(parent/'prediction_manifest.json')['runtime']
    for s in services:
        with urllib.request.urlopen(f'http://127.0.0.1:{s["port"]}/api/tags',timeout=10) as response:models=json.load(response)['models']
        if not any(m['name']==runtime['model'] and m['digest']==runtime['model_digest'] for m in models):raise RuntimeError('Judge model changed')
    cells=inventory(parent,stage);atomic(stage/'inventory.json',cells)
    tests=subprocess.run([runtime['python'],'-m','unittest','discover','-s',str(stage/'code'),'-p','test_judge.py'],capture_output=True,text=True)
    (stage/'tests.log').write_text(tests.stdout+tests.stderr)
    atomic(stage/'tests.json',dict(passed=tests.returncode==0,returncode=tests.returncode,at=time.time()))
    if tests.returncode:raise RuntimeError('Judge tests failed')
    preflight(parent,stage,services,runtime)
    files=list((stage/'code').glob('*.py'))+[stage/'inventory.json',stage/'tests.json',stage/'preflight/report.json',parent/'tasks.json']
    if cohort(stage):files.append(stage/'cohort.json')
    files+=list((parent/'data').glob('*/test.jsonl'))
    manifest=dict(protocol=VERSION,runtime=runtime,same_model_judge=True,provisional=True,
        primary_judge_user_decision='Qwen3-8B now; use a stronger judge with a future stronger-model campaign.',
        human_calibration='not_collected',seed=42,temperature=0,thinking=False,
        initial_output_tokens=2048,length_only_retry_cap=4096,context=32768,
        rubric_sha256=digest(dict(system=SYSTEM,schema=SCHEMA)),prediction_runs=len(cells),planned_items=100*len(cells),
        cohort=cohort(stage),
        future_optimizer_judgments='A separate frozen input cohort will use this same rubric and judge.',
        invalid_prediction_policy='Known schema failure: resolved fail without an LLM call; counted separately.',
        unknown_policy='Unresolved judge output or technical failure is never imputed; report coverage and full-panel bounds.',
        feedback_policy='Read-only assessment; no judgment is provided to any adaptation or optimization method.',
        files={str(p):sha(p) for p in files},sealed_at=time.time())
    manifest['seal_sha256']=digest(manifest);atomic(stage/'manifest.json',manifest)
    return manifest


def worker(parent, stage, cell_id, gpu):
    manifest=verify_manifest(stage/'manifest.json',stage)
    entry=next(v for v in load(stage/'inventory.json') if v['cell']['id']==cell_id)
    cell=entry['cell'];d=stage/'runs'/cell_id;d.mkdir(parents=True,exist_ok=True)
    lock=(d/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    task=load(parent/'tasks.json')[cell['dataset']]
    sources={r['record_id']:r['text'] for r in rows(parent/'data'/cell['dataset']/'test.jsonl')}
    native=Native(d/'calls',f'http://127.0.0.1:{11840+gpu}',manifest['runtime']['tokenizer'],42)
    old=load(d/'state.json').get('active_seconds',0) if (d/'state.json').exists() else 0;start=time.monotonic()
    def status(kind,error=None):
        records=[load(p) for p in sorted(d.glob('judgment_*.json'))]
        atomic(d/'state.json',dict(status=kind,**summarize(records,100),active_seconds=old+time.monotonic()-start,
            gpu=gpu,pid=os.getpid(),error_type=error,updated_at=time.time()))
    try:
        status('running')
        for item in entry['predictions']:
            check_stop(parent,stage)
            if sha(item['path'])!=item['sha256']:raise RuntimeError('Frozen prediction changed')
            destination=d/f'judgment_{item["index"]:03d}.json'
            if destination.exists():
                prior=load(destination)
                if prior['prediction_file_sha256']!=item['sha256'] or prior['judge_seal_sha256']!=manifest['seal_sha256']:raise RuntimeError('Judgment binding changed')
                continue
            prediction=load(item['path'])
            value=judge_one(native,task,sources[prediction['record_id']],prediction,'evaluation:'+item['sha256'])
            value.update(prediction_file_sha256=item['sha256'],output_sha256=prediction.get('output_sha256'),
                source_sha256=prediction['source_sha256'],judge_seal_sha256=manifest['seal_sha256'],committed_at=time.time())
            atomic(destination,value);status('running')
        summary=summarize([load(p) for p in d.glob('judgment_*.json')],100)
        status('complete' if summary['resolved']==100 else 'finished_with_unresolved')
    except BaseException as exc:
        status('paused' if isinstance(exc,KeyboardInterrupt) else 'failed',type(exc).__name__)
        raise


def report(stage):
    if not (stage/'inventory.json').exists():return
    entries=[]
    for v in load(stage/'inventory.json'):
        p=stage/'runs'/v['cell']['id']/'state.json'
        entries.append(dict(cell=v['cell'],source_stage=v['source_stage'],prediction_seal_sha256=v['prediction_seal_sha256'],
                            state=load(p) if p.exists() else dict(status='queued',processed=0,llm_judged=0,resolved=0)))
    manifest=load(stage/'manifest.json') if (stage/'manifest.json').exists() else {}
    result=dict(protocol=VERSION,provisional=True,same_model_judge=True,judge_seal_sha256=manifest.get('seal_sha256'),
        planned_items=100*len(entries),updated_at=time.time(),rows=entries,
        totals={k:sum(v['state'].get(k,0) for v in entries) for k in ['processed','llm_judged','resolved','passes','failures','invalid_predictions']})
    atomic(stage/'results.json',result)


def launch(parent, stage):
    stage.mkdir(parents=True,exist_ok=True)
    controller=(stage/'controller.lock').open('a');fcntl.flock(controller,fcntl.LOCK_EX|fcntl.LOCK_NB)
    atomic(stage/'dispatch.json',dict(pid=os.getpid(),start_identity=identity(os.getpid()),started_at=time.time()))
    shared=(parent/'prediction_controller.lock').open('a')
    spec=cohort(stage)
    while True:
        check_stop(parent,stage)
        if spec:
            precursor=parent/spec['precursor']
            ready=precursor.exists() and load(precursor).get('status')=='complete'
        else:
            precursor=parent/'stages/adaptation_r5_retained/pipeline_status.json'
            ready=precursor.exists() and load(precursor).get('status')=='prediction_complete'
        if ready:
            try:fcntl.flock(shared,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:pass
        atomic(stage/'pipeline_status.json',dict(status='waiting_for_predictions' if spec else 'waiting_for_retained_dc',at=time.time()))
        time.sleep(5)
    services=owned_services(parent)
    atomic(stage/'service_allocation.json',dict(used_gpus=[s['gpu'] for s in services],
        excluded_gpus_with_foreign_processes=OWNED_EXCLUDED,at=time.time()))
    atomic(stage/'pipeline_status.json',dict(status='development_preflight',at=time.time()))
    manifest=seal(parent,stage,services)
    pending=[];active={};finished={}
    for entry in load(stage/'inventory.json'):
        cell_id=entry['cell']['id'];p=stage/'runs'/cell_id/'state.json'
        if p.exists() and load(p)['status'] in ['complete','finished_with_unresolved']:finished[cell_id]=load(p)['status']
        else:pending.append(cell_id)
    while pending or active:
        stopped=(parent/'STOP').exists() or (stage/'STOP').exists()
        for gpu,(proc,cell_id,log) in list(active.items()):
            if proc.poll() is not None:
                log.close();p=stage/'runs'/cell_id/'state.json'
                finished[cell_id]=load(p)['status'] if p.exists() else 'failed_before_state';del active[gpu]
        for s in services:
            gpu=s['gpu']
            if stopped or not pending or gpu in active:continue
            cell_id=pending.pop(0);d=stage/'runs'/cell_id;d.mkdir(parents=True,exist_ok=True)
            log=(d/'worker.log').open('ab')
            proc=subprocess.Popen([manifest['runtime']['python'],str(stage/'code/evaluate.py'),'worker','--parent',str(parent),
                '--stage',str(stage),'--cell',cell_id,'--gpu',str(gpu)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            atomic(d/'worker.json',dict(pid=proc.pid,start_identity=identity(proc.pid),gpu=gpu,at=time.time()))
            active[gpu]=(proc,cell_id,log)
        status='paused' if stopped else 'running'
        atomic(stage/'queue.json',dict(status=status,active={str(g):v[1] for g,v in active.items()},queued=len(pending),finished=finished,at=time.time()))
        atomic(stage/'pipeline_status.json',dict(status=status,at=time.time()))
        atomic(parent/'ACTIVE_JUDGE_STAGE.json',dict(stage=str(stage),status=status,protocol=VERSION,provisional=True,at=time.time()))
        report(stage)
        if stopped and not active:break
        time.sleep(15)
    done=len(finished)==len(load(stage/'inventory.json')) and all(v=='complete' for v in finished.values())
    status='cohort_complete' if done else 'needs_attention'
    atomic(stage/'pipeline_status.json',dict(status=status,at=time.time()))
    atomic(stage/'queue.json',dict(status=status,active={},queued=len(pending),finished=finished,at=time.time()))
    atomic(parent/'ACTIVE_JUDGE_STAGE.json',dict(stage=str(stage),status=status,protocol=VERSION,provisional=True,at=time.time()))
    report(stage)


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['launch','worker','report'])
    parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--cell');parser.add_argument('--gpu',type=int)
    args=parser.parse_args()
    try:
        if args.action=='launch':launch(args.parent,args.stage)
        elif args.action=='worker':worker(args.parent,args.stage,args.cell,args.gpu)
        else:report(args.stage)
    except BaseException as exc:
        if args.action=='launch':atomic(args.stage/'pipeline_status.json',dict(status='paused' if isinstance(exc,KeyboardInterrupt) else 'failed',error_type=type(exc).__name__,at=time.time()))
        print(json.dumps(dict(status='failed',error_type=type(exc).__name__)))
        raise SystemExit(1)
