"""Report online stream denominators separately from reduced offline samples."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,os,sys
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'Storage/online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')
sys.path.insert(0,str(ROOT))
from experiments.reporting.results_layout import render
NAMES={'dreaddit':'Dreaddit','goemotions':'GoEmotions','cache':'CaChe','parlamint_gb':'ParlaMint-GB'}
METHODS=['dc_online_ref','dc_online_no_gt','ace_online_ref','ace_online_no_gt']
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def write(p,text):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(text);tmp.replace(p)
def render_online(result_rows=None):
    compact_rows=[]
    sup=read(ROOT/'Storage/budget_pilot'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/'supervisor.json');policy=read(RUN/'policy.json')
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    intro=f'# Online adaptation: 100 examples per dataset\n\nUpdated: {now}. Dreaddit/GoEmotions: DC/ACE × GT yes/no. CaChe/ParlaMint: DC/ACE, GT-free only. Total 12 rows, 100 ordered examples per row.\n\n'
    intro+='Qwen3-8B Q4_K_M; seed 42, thinking off. Each method starts with empty memory and receives the same IDs in the same order. Save each prediction before current-label feedback. Evaluate that pre-update prediction. Never feed judge outcomes into adaptation. Offline/full-test results remain separate.\n\n'
    if policy.get('offline_priority')==policy.get('online_priority')=='complete_100':intro+='User-authorized extra time: both offline and online prioritize completing 100 items and all judgments. No two-hour cutoff applies.\n\n'
    elif policy.get('online_priority')=='complete_100':intro+='Online N=100 completion takes priority over the earlier two-hour budget. Offline remains bounded.\n\n'
    else:intro+='N=100 is the fixed target. Until the pending time-budget preference is resolved, each dataset retains its existing shared two-hour wall-time deadline across offline and online work. Rows may stop incomplete; no smaller denominator is presented as a completed 100-example result.\n\n'
    intro+='Dreaddit/GoEmotions GT yes uses released labels, with binary/exact label-set ACC respectively. CaChe/ParlaMint use GT-free adaptation only; no reference labels are generated or supplied. Their ACC and reference agreement are N/A. Conformability is a reference-blind same-family LLM grounding judgment, not human verification. These are local task transfers, not exact paper reproductions.\n\n'
    if policy.get('uniform_policy'):intro += 'Fresh uniform-local-v1: no earlier inference or memory imported. Shared initial output caps 4096 (prediction/generator/optimization/reflector), 8192 (curator), 384 (judge); non-judge length-only escalation up to 16384 within context 32768. ACE/DC memory bound 4096; reject oversized updates and retain previous valid memory.\n\n'
    parts=[]
    for corpus,name in NAMES.items():
        d=RUN/corpus;phase=sup.get('corpora',{}).get(corpus,{}).get('phases',{}).get('online',{});q=read(d/'queue.json');supervised=corpus in ('dreaddit','goemotions')
        text=f'## {name}: online N=100\n\nQueue: {phase.get("status","queued")}; {q.get("method","—")} / {q.get("stage","—")} {q.get("n",0)}/100.\n\n'
        text+='| Method | GT | Acc % | Reference agreement % | Conformability % | Progress |\n| --- | --- | ---: | ---: | ---: | --- |\n'
        rows=[json.loads(x) for x in (d/'data/test.jsonl').read_text().splitlines()] if (d/'data/test.jsonl').exists() else []
        for method in (METHODS if supervised else ['dc_online_no_gt','ace_online_no_gt']):
            md=d/method;state=read(md/'state.json');quality=[json.loads(x) for x in (md/'quality.jsonl').read_text().splitlines()] if (md/'quality.jsonl').exists() else []
            count=len(list(md.glob('prediction_[0-9]*.json')));unknown=sum(x.get('decision') is None for x in quality)
            done=state.get('status')=='complete' and state.get('n')==100 and count==100
            acc='—' if supervised else 'N/A';agreement='—' if supervised else 'N/A';conf='—'
            if done and supervised:
                correct=0
                for i,row in enumerate(rows):
                    pred=read(md/f'prediction_{i:04d}.json');assert pred['record_id']==row['record_id']
                    if supervised:target=sorted(map(str,row['target']))
                    else:
                        ref=read(d/'references'/f'{i:04d}.json');assert ref['record_id']==row['record_id'];target=ref['topic_ids']
                    correct+=pred['predicted_topics']==target
                assert len(rows)==100
                if supervised:acc=f'{correct:.2f}'
                else:agreement=f'{correct:.2f}'
            if len(quality)==100 and not unknown:conf=f"{sum(x['decision'] is True for x in quality):.2f}"
            gt=('✓' if supervised else '✓†') if method.endswith('_ref') else '✗'
            compact_rows.append(dict(corpus=corpus,phase='online',method=method,gt=gt,
                acc=acc,conf=conf,predicted=count,updated=state.get('n',0),
                judged=len(quality),unknown=unknown,queue_method=q.get('method'),
                queue_stage=q.get('stage','prediction')))
            text+=f'| {"DC (CU)" if method.startswith("dc_") else "ACE"} | {gt} | {acc} | {agreement} | {conf} | {state.get("status","queued")}; saved {count}/100; updated {state.get("n",0)}/100; judged {len(quality)}/100; unresolved {unknown} |\n'
        text+='\n'
        write(d/'METRICS.md',intro+text)
        write(d/'RESULTS.md',render([r for r in compact_rows if r['corpus']==corpus],sup,now,ROOT/'Storage',policy,d/'METRICS.md'))
        parts.append(text)
    result=intro+''.join(parts)
    write(RUN/'METRICS.md',result)
    write(RUN/'RESULTS.md',render(compact_rows,sup,now,ROOT/'Storage',policy,RUN/'METRICS.md'))
    if result_rows is not None:result_rows.extend(compact_rows)
    return result
if __name__=='__main__':render_online()
