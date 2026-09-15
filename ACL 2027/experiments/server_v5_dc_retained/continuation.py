"""Prepare and launch a separately sealed retained-memory DC continuation."""
from pathlib import Path
import argparse, fcntl, hashlib, json, os, shutil, subprocess, sys, time


def prepare(parent, stage):
    sys.path[:0] = [str(stage/'code'), str(parent/'code')]
    from core import atomic, load, digest, rows
    from run import verify
    old = parent/'stages/adaptation_r4'
    original = verify(old)
    assert not (stage/'plan.json').exists(), 'Already prepared'
    plan = load(old/'plan.json')
    plan['cells'] = [c for c in plan['cells'] if c['dataset']=='goemotions' and c['adaptation_gt']=='yes']
    assert len(plan['cells']) == 3
    plan.update(protocol='four-corpus-server-v5-dc-retained-r5', stage_runs=3, stage_predictions=300,
        predecessor='r4 GoEmotions DC GT yes, all three seeds; compatible successful prefixes reused',
        development_gate='Six cached real development transitions unchanged; 20 software checks and an exact zero-call failed-boundary transition proof.',
        failure_policy='Reject verified exhausted malformed/length/incomplete curator output and retain previous memory. Infrastructure, source, GT, and generator failures still stop. No invented curator response. This changes r4 fail-stop semantics and is a separately reported DC variant.')
    plan['task_transfer']['failures'] = plan['failure_policy']
    atomic(stage/'plan.json',plan)
    shutil.copy2(old/'orders.json',stage/'orders.json')
    shutil.copytree(old/'upstream',stage/'upstream')
    prefix = {}
    for cell in plan['cells']:
        source = old/'runs'/cell['id']; dest = stage/'runs'/cell['id']; dest.mkdir(parents=True)
        state = load(source/'state.json')
        assert state['status'] == ('failed' if cell['seed']==44 else 'prediction_complete')
        files = list(source.glob('prediction_*.json'))
        for name in ['calls','updates','feedback_receipts']:
            files.extend((source/name).glob('*.json'))
        prefix[cell['id']] = {}
        for path in files:
            rel = path.relative_to(source); output=dest/rel; output.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,output)
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            assert hashlib.sha256(output.read_bytes()).hexdigest()==sha
            prefix[cell['id']][str(rel)]=sha
        atomic(dest/'state.json',dict(state,status='queued' if cell['seed']==44 else 'prediction_complete'))
        atomic(stage/'inheritance'/cell['id']/'original_state.json',state)
    atomic(stage/'IMPORT_PREFIXES.json',prefix)
    cell=next(c for c in plan['cells'] if c['seed']==44); directory=stage/'runs'/cell['id']
    key='aeaf22b9a8266e60857b0263891c0518eab8ea6aa04a96fc0c9ce0e155f8b7cc'
    failed=load(directory/'calls'/(key+'.attempt0.json'))
    request=load(directory/'calls'/(key+'.request.json'))
    assert digest(request)==failed['request_sha256']
    evidence_files={}
    for attempt in range(3):
        path=directory/'calls'/(key+f'.attempt{attempt}.json'); value=load(path)
        assert value['status']=='error' and value['error_type']=='RuntimeError'
        assert value['key']==failed['key'] and value['request_sha256']==failed['request_sha256']
        evidence_files[str(path.relative_to(directory))]=hashlib.sha256(path.read_bytes()).hexdigest()
    diagnostic=parent/'recovery_dc_20260914_1/diagnostics/goemotions_incomplete_response'
    assert digest(load(diagnostic/'request.json'))==failed['request_sha256']
    for src,name in [('response.bin','response.json'),('metadata.json','metadata.json'),('request.json','request.json')]:
        dest=directory/'inherited_diagnostic'/name;dest.parent.mkdir(exist_ok=True)
        shutil.copy2(diagnostic/src,dest)
        evidence_files[str(dest.relative_to(directory))]=hashlib.sha256(dest.read_bytes()).hexdigest()
    proof=dict(structured_key=failed['key'].removesuffix(':format:0'),request_sha256=failed['request_sha256'],
        evidence_files=evidence_files,diagnostic_response='inherited_diagnostic/response.json',
        reason='Original three incomplete production attempts plus a matching separate diagnostic. Consume once without another model request.')
    atomic(directory/'inherited_failure.json',proof)
    atomic(stage/'REVISION.json',dict(policy=plan['failure_policy'], predecessor_seal=original['seal_sha256'],
        scope='Three GoEmotions online DC GT-yes seeds. Seeds42/43 imported complete because no unusable curator was retained; seed44 resumes its valid prefix.',
        unchanged=['prompts','schemas','model','seeds','data/order','GT visibility','token caps','4096-token memory budget'],
        imported_diagnostic_not_evaluation=True,at=time.time()))
    env=dict(os.environ,PYTHONPATH=str(stage/'code')+os.pathsep+str(parent/'code'),
        ADAPTATION_UPSTREAM=str(stage/'upstream'),PYTHONDONTWRITEBYTECODE='1')
    with (stage/'tests.log').open('wb') as log:
        result=subprocess.run([plan['runtime']['python'],'-m','unittest','discover','-s',str(stage/'code'),'-p','test_*.py','-v'],env=env,stdout=log,stderr=log)
    assert result.returncode==0,'Software tests failed'
    atomic(stage/'tests.json',dict(passed=True,tests=20,at=time.time()))
    # Real development replay proves unchanged successful decisions and memory.
    from retained_policy import Native
    from adapters import DC,Upstream
    from unittest.mock import patch
    task=load(parent/'tasks.json')['goemotions'];up=Upstream(stage/'upstream')
    devcell=next(c for c in plan['cells'] if c['seed']==42)
    source=old/'preflight'/devcell['id']; dest=stage/'preflight'/devcell['id']
    shutil.copytree(source,dest)
    native=Native(dest/'calls','http://127.0.0.1:11840',plan['runtime']['tokenizer'],42)
    devdata={r['record_id']:r for r in rows(parent/'data/goemotions/dev.jsonl')}
    memory='(empty)';next_id=1
    with patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected inference during replay')):
        for i in range(6):
            prediction=load(dest/f'prediction_{i:03d}.json'); prior=load(dest/'updates'/f'evaluation_{i:03d}.json')
            rid=prediction['record_id']; item=devdata[rid]
            result=DC(native,up,task).step(dict(record_id=rid,text=item['text']),memory,next_id,
                f'evaluation:{i}:{rid}',prediction['output'],lambda v: (_ for _ in ()).throw(AssertionError('Regeneration')),
                lambda item=item:item['target'])
            for field,value in result.items(): assert prior[field]==value,field
            memory,next_id=result['memory'],result['next_id']
        # Reconstruct the actual failed request exactly; rejected update changes no memory.
        pred=load(directory/'prediction_019.json');before=load(directory/'updates/evaluation_018.json')
        item=next(r for r in rows(parent/'data/goemotions/test.jsonl') if r['record_id']==pred['record_id'])
        native=Native(directory/'calls','http://127.0.0.1:11840',plan['runtime']['tokenizer'],44)
        result=DC(native,up,task).step(dict(record_id=item['record_id'],text=item['text']),before['memory'],before['next_id'],
            f"evaluation:19:{item['record_id']}",pred['output'],lambda v: (_ for _ in ()).throw(AssertionError('Regeneration')),
            lambda:item['target'])
        assert result['memory']==before['memory'] and result['next_id']==before['next_id'] and not result['accepted']
        assert result['failure_evidence']['new_inference_calls']==0 and 'curator_response' not in result
    atomic(stage/'preflight/report.json',dict(cases=1,passed=1,results=[dict(cell=devcell['id'],status='prediction_complete',predicted=6,updated=6)],
        inference_calls=0,real_failed_boundary_verified=True,successful_development_transitions=6,at=time.time()))
    for cell_id,files in prefix.items():
        assert all(hashlib.sha256((stage/'runs'/cell_id/p).read_bytes()).hexdigest()==sha for p,sha in files.items())
    atomic(stage/'PREPARATION_AUDIT.json',dict(passed=True,imported_files=sum(map(len,prefix.values())),
        unchanged_development_transitions=6,zero_call_retained_transition_verified=True,at=time.time()))
    paths=list((stage/'code').glob('*.py'))+list((stage/'upstream').rglob('*'))
    paths += [stage/name for name in ['plan.json','orders.json','REVISION.json','tests.json','IMPORT_PREFIXES.json','PREPARATION_AUDIT.json','preflight/report.json']]
    paths += [directory/'inherited_failure.json']
    manifest=dict(plan,files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},
        admitted_cells=plan['cells'],withheld_cells=[],preflight_cases=1,sealed_at=time.time())
    # Bind every unchanged predecessor source/input file as well.
    manifest['files'].update(original['files'])
    manifest['seal_sha256']=digest(manifest)
    atomic(stage/'manifest.json',manifest)
    print(json.dumps(dict(prepared=True,admitted_runs=3,inference_calls=0,seal=manifest['seal_sha256'])))


def launch(parent, stage):
    sys.path[:0]=[str(stage/'code'),str(parent/'code')]
    from core import atomic,load
    from stage import identity
    # The predecessor holds the global lock until CaChe reaches its final checkpoint.
    atomic(stage/'dispatch.json',dict(pid=os.getpid(),start_identity=identity(os.getpid()),started_at=time.time()))
    while True:
        if (parent/'STOP').exists() or (stage/'STOP').exists():return
        lock=(parent/'prediction_controller.lock').open('a')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close();atomic(stage/'pipeline_status.json',dict(status='validated_waiting_for_predecessor',at=time.time()))
            time.sleep(5);continue
        lock.close();break
    plan=load(stage/'plan.json')
    env=dict(os.environ,PYTHONPATH=str(stage/'code')+os.pathsep+str(parent/'code'),PYTHONDONTWRITEBYTECODE='1')
    with (stage/'controller.log').open('ab') as log:
        child=subprocess.Popen([plan['runtime']['python'],str(stage/'code/stage.py'),'launch','--stage',str(stage)],
            env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    while True:
        code=child.poll(); queue=load(stage/'queue.json') if (stage/'queue.json').exists() else {}
        state='running' if code is None else 'prediction_complete' if code==0 and all(
            load(stage/'runs'/c['id']/'state.json')['status']=='prediction_complete' for c in plan['cells']) else 'needs_attention'
        atomic(stage/'pipeline_status.json',dict(status=state,pid=child.pid,exit_code=code,at=time.time()))
        atomic(parent/'ACTIVE_ADAPTATION_STAGE.json',dict(active_stage=stage.name,status='retained_dc_'+state,
            continuing_ace_stage='adaptation_r3',preserved_dc_stage='adaptation_r4',
            recovery_revision='dc-r4-unicode-transport-recovery-v1',retained_policy='dc-verified-output-rejection-v1',at=time.time()))
        if code is not None:break
        time.sleep(15)
    prefix=load(stage/'IMPORT_PREFIXES.json');changed=[]
    for cell_id,files in prefix.items():
        for name,sha in files.items():
            if hashlib.sha256((stage/'runs'/cell_id/name).read_bytes()).hexdigest()!=sha:changed.append(cell_id+'/'+name)
    retained=[]
    for c in plan['cells']:
        memory='(empty)';next_id=1;d=stage/'runs'/c['id']
        from core import digest,rows
        sources={r['record_id']:r for r in rows(parent/'data/goemotions/test.jsonl')}
        for p in sorted(d.glob('prediction_*.json')):
            v=load(p);assert v['valid'] and v['memory_before_sha256']==digest(memory) and v['output_sha256']==digest(v['output'])
            assert v['source_sha256']==hashlib.sha256(sources[v['record_id']]['text'].encode()).hexdigest()
            u=load(d/'updates'/f"evaluation_{v['index']:03d}.json")
            assert u['prediction_sha256']==v['output_sha256'] and u['memory_before_sha256']==digest(memory)
            assert u['memory_after_sha256']==digest(u['memory'])
            receipt=load(d/'feedback_receipts'/f"evaluation_{v['index']:03d}.json")
            assert receipt['reference_sha256']==digest(sources[v['record_id']]['target'])
            assert v['committed_at']<=receipt['revealed_at']<=u['completed_at']
            if u['decision']=='rejected_unusable_curator_retained_prior':
                assert not u['accepted'] and u['memory']==memory and u['next_id']==next_id and u['candidate_sha256'] is None
                assert 'curator_response' not in u and u['failure_evidence']
                retained.append(dict(cell=c['id'],index=v['index']))
            memory,next_id=u['memory'],u['next_id']
    atomic(stage/'FINAL_PREFIX_AUDIT.json',dict(passed=not changed,changed=changed,
        imported_files=sum(map(len,prefix.values())),retained_updates=retained,at=time.time()))
    assert not changed,'Imported evidence changed'


if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','launch'])
    parser.add_argument('--parent',type=Path,required=True);parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args();globals()[args.action](args.parent,args.stage)
