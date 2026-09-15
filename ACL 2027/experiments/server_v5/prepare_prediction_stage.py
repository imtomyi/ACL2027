"""Freeze first-stage datasets, prompts, demonstrations, orders and code before evaluation."""
from pathlib import Path
import argparse,hashlib,json,random,os
from core import Native,atomic,load,rows,digest,output_schema,question

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    if (root/'prediction_manifest.json').exists():raise RuntimeError('Prediction stage already sealed')
    runtime=load(root/'runtime.json');tasks=load(root/'tasks.json');n=Native(root/'preparation_tokenizer', 'http://127.0.0.1:11840',runtime['tokenizer'])
    orders={};demonstrations={};cells=[]
    for c,task in tasks.items():
        test=rows(root/'data'/c/'test.jsonl');train=rows(root/'data'/c/'train.jsonl');assert len(test)==len(train)==100
        orders[c]={};demonstrations[c]={}
        for seed in [42,43,44]:
            ids=[r['record_id'] for r in test]
            if seed!=42:random.Random(seed).shuffle(ids)
            orders[c][str(seed)]=ids
            if c in ['dreaddit','goemotions']:
                candidates=sorted(train,key=lambda r:hashlib.sha256(f'v5-icl:{seed}:{r["record_id"]}'.encode()).hexdigest());selected=[];texts=[]
                for row in candidates:
                    example=json.dumps({'source':row['text'],'label_ids':row['target']},ensure_ascii=False)
                    trial='\n\n'.join(texts+[example])
                    # Include the complete demonstrations envelope in the learned-context cap.
                    if len(n.tokenizer.encode('Use these fixed labeled demonstrations for the task. Follow the final response schema for the new source.\n'+trial))>4096:continue
                    selected.append(row['record_id']);texts.append(example)
                    if len(texts)==8:break
                assert len(texts)==8,'Eight demonstrations cannot fit shared learned-context cap'
                prefix='\n\n'.join(texts);demonstrations[c][str(seed)]={'record_ids':selected,'text':prefix,'tokens':len(n.tokenizer.encode(prefix)),'selection':'seeded ID-hash order; greedily retain complete examples within 4096-token envelope; exactly 8'}
            for method in ['base']+(['icl'] if c in ['dreaddit','goemotions'] else []):
                cells.append({'id':f'{c}__{method}__seed{seed}','dataset':c,'method':method,'seed':seed,'phase':'baseline' if method=='base' else 'offline','adaptation_gt':'not_applicable' if method=='base' else 'yes','n':100})
        # Bound every source prompt before launch without seeing model answers.
        for row in test:
            for seed in [42,43,44]:
                messages=[{'role':'user','content':question(task,row)}]
                if c in ['dreaddit','goemotions']:messages.insert(0,{'role':'system','content':'Use these fixed labeled demonstrations for the task. Follow the final response schema for the new source.\n'+demonstrations[c][str(seed)]['text']})
                assert n.count(messages)+4096<=32768,'Context reserve exceeded'
    atomic(root/'orders.json',orders);atomic(root/'demonstrations.json',demonstrations)
    files={}
    for p in list((root/'code').glob('*.py'))+list((root/'data').rglob('*.json*'))+[root/'orders.json',root/'demonstrations.json',root/'tasks.json',root/'runtime.json',root/'AMENDMENTS.json']:
        files[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    # Interleave corpora/methods before repetitions to expose all initial conditions promptly.
    cells.sort(key=lambda c:(c['seed'],['base','icl'].index(c['method']),['dreaddit','goemotions','cache','parlamint_gb'].index(c['dataset'])))
    manifest={'protocol':'four-corpus-server-v5-prediction-stage-r1','parent_design':'four-corpus-server-v5','stage':'Base/ICL predictions only; other adapters and judge not represented as ready','launch_authorized':True,'cells':cells,'runtime':runtime,'files':files,'sample_n':100,'seeds':[42,43,44],'full_panel_runs':84,'judge':None,'judge_policy':'Separate later seal, blind to methods and aggregate test performance; no judge feedback to generation','evidence_policy':'Raw model response retained; exact-quote occurrence and reported offset validity reported separately. Deterministic unique exact anchors do not alter label decisions or raw quotes. No fuzzy repair.','historical_score_reuse':False,'online_adaptation':False}
    manifest['seal_sha256']=digest(manifest);atomic(root/'prediction_manifest.json',manifest)
    print(json.dumps({'sealed_runs':len(cells),'predictions':len(cells)*100,'model_calls':0,'demo_tokens':{c:{s:v['tokens'] for s,v in d.items()} for c,d in demonstrations.items() if d}}))
if __name__=='__main__':main()
