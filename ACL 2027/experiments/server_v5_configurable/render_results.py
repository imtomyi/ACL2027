"""Future-run report: every progress/metric denominator comes from sealed sizes."""
from pathlib import Path
import argparse,json,statistics
from sizes import CORPORA,cell_sizes,panel_target,manifest as sampling_manifest


def load(p):return json.loads(p.read_text())
def key(c):return tuple(c[k] for k in ['dataset','phase','method','adaptation_gt','seed'])
def ready(r,metric):
    c,s,m=r['cell'],r['state'],r['metrics']
    if s.get('attempted')!=c['n']:return None
    if metric=='conformability' and s.get('judged')!=c['n']:return None
    return m.get(metric)

def report(root,protocol):
    root=Path(root);selected={};sources=[]
    candidates=[(root,'prediction_manifest.json')]+[(p.parent,'manifest.json') for p in (root/'stages').glob('*/manifest.json')]
    entries=[]
    for d,name in candidates:
        if (d/name).exists() and (d/'results.json').exists():
            m=load(d/name);entries.append((m.get('sealed_at',0),d,m,load(d/'results.json')))
    for _,d,m,result in sorted(entries,key=lambda x:x[0]):
        admitted={c['id'] for c in m.get('admitted_cells',m['cells'])}
        for r in result['rows']:
            if r['cell']['id'] in admitted or key(r['cell']) not in selected:selected[key(r['cell'])]=r
        sources.append(dict(stage=str(d),seal_sha256=m['seal_sha256']))
    rows=[]
    for condition in protocol['conditions']:
        for seed in protocol['seeds']:
            c=dict(condition,seed=seed,**cell_sizes(root,condition['dataset'],condition['phase'],condition['method']))
            row=selected.get(key(c),dict(cell=c,state={'status':'unstarted'},metrics={}))
            if row['cell']['n']!=c['n']:raise ValueError('Mixed sample-size revisions cannot share one result panel')
            rows.append(row)
    counts=sampling_manifest(root)['counts'];total=sum(r['cell']['n'] for r in rows)
    lines=['# Configurable experiment results','',
        'Frozen sample counts: `'+json.dumps(counts,sort_keys=True)+'`.','',
        f'Valid evaluation predictions: {sum(r["state"].get("predicted",0) for r in rows)}/{total}.',
        f'Memory updates: {sum(r["state"].get("updated",0) for r in rows)}/{sum(r["cell"]["update_n"] for r in rows)}.',
        'Acc counts invalid outputs as incorrect over the entire frozen evaluation denominator. F1 availability follows the sealed scorer. GTX thematic accuracy remains N/A. Judging and conditional metrics remain pending until measured.','',
        '| **Dataset** | **Phase / method** | **GT** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability %** | **Valid / target** |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for condition in protocol['conditions']:
        subset=[r for r in rows if all(r['cell'][k]==condition[k] for k in ['dataset','phase','method','adaptation_gt'])]
        def aggregate(metric):
            if metric!='conformability' and condition['dataset'] in ['cache','parlamint_gb']:return 'N/A'
            values=[ready(r,metric) for r in subset]
            if any(v is None for v in values):return '—'
            return f'{statistics.mean(values):.2f} ± {statistics.stdev(values):.2f}'
        lines.append('| '+ ' | '.join([condition['dataset'],condition['phase']+' / '+condition['method'],condition['adaptation_gt'],
            *[aggregate(k) for k in ['accuracy','micro_f1','macro_f1','conformability']],
            f'{sum(r["state"].get("predicted",0) for r in subset)}/{sum(r["cell"]["n"] for r in subset)}'])+' |')
    lines+=['','| **Dataset** | **Phase / method** | **GT** | **Seed** | **Valid / attempted / target** | **Train / target** | **Updates / target** | **Judged / target** | **Status** |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in rows:
        c,s=r['cell'],r['state'];train=f'{s.get("adapted",0)}/{c["train_n"]}' if c['phase']=='offline' and c['method']=='ace' else '—'
        lines.append('| '+' | '.join([c['dataset'],c['phase']+' / '+c['method'],c['adaptation_gt'],str(c['seed']),
            f'{s.get("predicted",0)}/{s.get("attempted",0)}/{c["n"]}',train,
            f'{s.get("updated",0)}/{c["update_n"]}',f'{s.get("judged",0)}/{c["n"]}',s['status']])+' |')
    return '\n'.join(lines)+'\n',dict(counts=counts,prediction_target=total,rows=rows,sources=sources)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True)
    a=p.parse_args();text,data=report(a.root,load(a.protocol))
    (a.root/'results.md').write_text(text);(a.root/'results.snapshot.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'rows':len(data['rows']),'prediction_target':data['prediction_target']}))
