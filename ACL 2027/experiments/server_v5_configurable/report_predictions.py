"""Derive scores from committed predictions; never infer unfinished results."""
from pathlib import Path
import argparse,json,time
from core import load,rows,atomic

def scores(pred,gold,task):
    expected_n=len(gold)
    ids=[x['record_id'] for x in pred]
    if len(set(ids))!=len(ids) or set(ids)-set(gold):raise ValueError('Prediction identity mismatch')
    import numpy as np
    from sklearn.metrics import (accuracy_score,precision_recall_fscore_support,confusion_matrix,multilabel_confusion_matrix,balanced_accuracy_score,matthews_corrcoef,cohen_kappa_score,hamming_loss,jaccard_score)
    valid=[x for x in pred if x['valid']];n=len(pred)
    correct=sum(sorted(x['output']['label_ids'])==sorted(gold[x['record_id']]['target']) for x in valid)
    result={'prediction_n':n,'valid_n':len(valid),'correct':correct,'accuracy':100*correct/expected_n if n==expected_n else None,'valid_accuracy':100*correct/len(valid) if valid else None,'accuracy_status':'complete' if n==expected_n else 'partial'}
    if n!=expected_n or len(valid)!=expected_n:return result
    labels=task['labels'];single=task['single_label']
    if single:
        y=np.array([gold[x['record_id']]['target'][0] for x in pred]);p=np.array([x['output']['label_ids'][0] for x in pred])
    else:
        y=np.array([[int(k in gold[x['record_id']]['target']) for k in labels] for x in pred]);p=np.array([[int(k in x['output']['label_ids']) for k in labels] for x in pred])
    for avg in ['micro','macro','weighted']+([] if single else ['samples']):
        pr,rec,f1,_=precision_recall_fscore_support(y,p,average=avg,labels=labels if single else None,zero_division=0)
        result.update({avg+'_precision':100*float(pr),avg+'_recall':100*float(rec),avg+'_f1':100*float(f1)})
    pr,rec,f1,support=precision_recall_fscore_support(y,p,average=None,labels=labels if single else None,zero_division=0)
    result['per_label']=[{'label_id':k,'precision':100*float(a),'recall':100*float(b),'f1':100*float(c),'support':int(d)} for k,a,b,c,d in zip(labels,pr,rec,f1,support)]
    if single:
        cm=confusion_matrix(y,p,labels=labels);tn,fp,fn,tp=cm.ravel();result.update(confusion=cm.tolist(),balanced_accuracy=100*float(balanced_accuracy_score(y,p)) if len(set(y))==2 else None,mcc=float(matthews_corrcoef(y,p)),kappa=float(cohen_kappa_score(y,p)) if len(set(y)|set(p))>1 else None,stress_f1=100*float(f1[1]),specificity=100*int(tn)/int(tn+fp) if tn+fp else None)
    else:
        result.update(confusion=multilabel_confusion_matrix(y,p).tolist(),hamming_loss=100*float(hamming_loss(y,p)),sample_jaccard=100*float(jaccard_score(y,p,average='samples',zero_division=0)),supported_macro_f1=100*float(f1[support>0].mean()) if any(support>0) else None,predicted_cardinality=float(p.sum(axis=1).mean()),true_cardinality=float(y.sum(axis=1).mean()),empty_label_rate=100*float((p.sum(axis=1)==0).mean()),neutral_colabel_rate=100*float(((p[:,27]==1)&(p.sum(axis=1)>1)).mean()))
    return result

def report(root):
    manifest=load(root/'prediction_manifest.json');tasks=load(root/'tasks.json');values=[]
    for cell in manifest['cells']:
        d=root/'runs'/cell['id'];pred=[load(p) for p in sorted(d.glob('prediction_*.json'))];state=load(d/'state.json') if (d/'state.json').exists() else {'status':'queued','active_seconds':0}
        task=tasks[cell['dataset']];gold={x['record_id']:x for x in rows(root/'data'/cell['dataset']/'test.jsonl')}
        metric=scores(pred,gold,task) if cell['dataset'] in ['dreaddit','goemotions'] else {'accuracy':None,'accuracy_status':'not_applicable_no_reference'}
        anchors=[a for x in pred if x['valid'] for a in x['literal_anchors']];quotes=len(anchors);literal=sum(x['literal_match'] for x in anchors);offset=sum(x['reported_offset_valid'] for x in anchors)
        metric.update(literal_exact_quote_validity=100*literal/quotes if quotes else None,reported_offset_validity=100*offset/quotes if quotes else None,submitted_quotes=quotes,prediction_coverage=sum(x['valid'] for x in pred),conformability=None,conformability_status='pending_judge_selection')
        row=dict(cell=cell,state=state,metrics=metric);values.append(row);atomic(d/'metrics.json',metric)
    total=sum(r['state'].get('predicted',0) for r in values);attempted=sum(r['state'].get('attempted',0) for r in values)
    target=sum(c['n'] for c in manifest['cells']);full_target=manifest['full_panel_prediction_target']
    overview={'protocol':manifest['protocol'],'scope':'First stage: 18 Base/ICL seed runs of the planned 84-run Qwen3-8B panel','predicted':total,'attempted':attempted,'stage_prediction_target':target,'full_panel_prediction_target':full_target,'judged':0,'updated_at':time.time(),'rows':values}
    atomic(root/'results.json',overview)
    lines=['# Qwen3-8B server prediction stage','',f'Updated UTC: {time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())}. Predicted {total}/{target} for this stage. Full planned panel: 84 runs / {full_target} predictions. Judgments: pending.','',
      'This is the first sealed prediction stage, not the completed v5 comparison. Four Base and two ICL conditions, seeds 42/43/44. Other method adapters remain pending validation. Historical scores are not imported.','',
      '| **Dataset** | **Method** | **Seed** | **Predicted** | **Acc %** | **Micro-F1 %** | **Macro-F1 %** | **Conformability** | **Active min** | **Status** |',
      '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |']
    for r in values:
        c,s,m=r['cell'],r['state'],r['metrics'];fmt=lambda k:f'{m[k]:.2f}' if m.get(k) is not None and s.get('attempted')==c['n'] else '—'
        acc='N/A' if c['dataset'] in ['cache','parlamint_gb'] else fmt('accuracy')
        lines.append(f"| {c['dataset']} | {c['method']} | {c['seed']} | {s.get('predicted',0)}/{c['n']} | {acc} | {fmt('micro_f1')} | {fmt('macro_f1')} | PENDING | {s.get('active_seconds',0)/60:.1f} | {s['status']} |")
    lines+=['','Dreaddit accuracy is binary exact-label accuracy. GoEmotions accuracy is exact-set accuracy over the fixed 28 labels; official neutral co-labels remain valid. CaChe/ParlaMint have no validated label GT.','',
      'Raw reported evidence offsets remain saved and are scored separately. Literal anchors use exact Unicode substring matching only, with no fuzzy text repair. A unique match or valid model offset resolves a location; otherwise location remains unresolved.','',
      'Task scores finalize independently of judging. A prediction-complete row is not a fully judged experiment. See metrics.json for per-label metrics and diagnostic denominators. Other registered metrics remain pending or conditional.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n');(root/'METRICS.md').write_text('# Prediction-stage metrics\n\nMachine-readable scores and denominators are in results.json and runs/*/metrics.json.\n\n'+ '\n'.join(lines[2:])+'\n')
    return {'predicted':total,'target':target,'judged':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();print(json.dumps(report(a.root)))
