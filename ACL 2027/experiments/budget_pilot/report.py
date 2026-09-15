"""Report actual reduced-run denominators; keep historical full-run results separate."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,os,sys
ROOT=Path(__file__).resolve().parents[2];STORAGE=ROOT/'Storage';RUN=STORAGE/'budget_pilot'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')
OFFLINE=STORAGE/'offline100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')
sys.path.insert(0,str(ROOT))
from experiments.reporting.results_layout import render
N={c:100 for c in ['goemotions','dreaddit','cache','parlamint_gb']}
NAMES={'goemotions':'GoEmotions','dreaddit':'Dreaddit','cache':'CaChe','parlamint_gb':'ParlaMint-GB'}

def read(p):return json.loads(p.read_text()) if p.exists() else {}
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,t):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(t);tmp.replace(p)

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds');sup=read(RUN/'supervisor.json')
    result_rows=[];policy=read(STORAGE/'online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/'policy.json')
    text=f'# Four datasets: 100 shared evaluation items each\n\nUpdated: {now}. User-authorized new protocol: at most 2 hours of wall time per dataset, serial execution (up to about 8 hours total, plus transition overhead).\n\n'
    text+='Model: Qwen3-8B Q4_K_M, thinking off, seed 42. There are 400 unique evaluation items: 100 per dataset. Every offline and online method uses the same ordered 100 IDs for its dataset; repeated method predictions do not increase the unique sample count. Training, demonstration and adaptation pools are separate. Compatible saved per-item predictions and frozen offline playbooks may be reused with a reuse_manifest; scores are recomputed for N=100. Small pilot results have high sampling uncertainty and are not full-test benchmarks.\n\n'
    text+='Supervised offline: Base, 8-example ICL, MIPROv2 (2 candidates, 4 trials), GEPA (96 metric-call budget). Offline and online both evaluate N=100, with separate method state. CaChe and ParlaMint run first; offline runs Base and ACE GT-free only using the existing provisional task. GPT-5 remains outside these queues; ICL/MIPROv2/GEPA are not implemented for the provisional corpora.\n\n'
    text+='CaChe/ParlaMint are GT-free only, with no reference annotations. ACC and reference agreement are N/A. GoEmotions is queued after the priority corpora. The superseded 128-item worker was stopped; compatible predictions and optimizer response caches are preserved for the 100-item run. No claim is made that its in-memory optimizer search resumed. Conformability is a reference-blind same-family LLM grounding judgment, not human verification. Unresolved judgments remain unknown. Offline test labels never feed adaptation; online feedback follows the current prediction.\n\n'
    text+='A 2-hour deadline stops a corpus gracefully and proceeds to the next. Incomplete rows remain incomplete; the deadline does not guarantee all rows finish. A resumed corpus retains its original deadline.\n\n'
    for c in ['dreaddit','goemotions','cache','parlamint_gb']:
        d=OFFLINE/c;n=N[c];entry=sup.get('corpora',{}).get(c,{});q=read(d/'queue.json')
        text+=f"## {NAMES[c]}\n\nOffline evaluation N={n} (same IDs as online). Corpus queue: {entry.get('status','queued')}; {q.get('method','—')} / {q.get('stage','—')} {q.get('n',0)}/{q.get('total',n)}.\n\n"
        if entry.get('deadline') and entry.get('status')=='running' and policy.get('offline_priority')!='complete_100':
            deadline=datetime.fromtimestamp(entry['deadline'],ZoneInfo('Asia/Seoul')).strftime('%H:%M:%S KST');text+=f'Wall-time deadline: {deadline}.\n\n'
        methods=['base','icl','miprov2','gepa'] if c in ('goemotions','dreaddit') else ['base','ace_offline_no_gt']
        text+='| Method | Acc % | Reference agreement % | Micro-F1 % | Macro-F1 % | Conformability % | Progress |\n| --- | ---: | ---: | ---: | ---: | ---: | --- |\n'
        for m in methods:
            md=d/m if c in ('goemotions','dreaddit') else d/c/m
            s=read(md/'state.json');quality=lines(md/'quality.jsonl');done=s.get('status')=='complete' and s.get('n')==n
            unknown=sum(x.get('decision') is None for x in quality)
            conf=f"{100*sum(x.get('decision') is True for x in quality)/n:.2f}" if len(quality)==n and not unknown else '—'
            scores=s.get('scores',{});acc=micro=macro=agreement='—'
            if c in ('goemotions','dreaddit') and done:
                acc=f"{100*scores['acc']:.2f}";micro=f"{100*scores['micro_f1']:.2f}";macro=f"{100*scores['macro_f1']:.2f}"
            if c in ('cache','parlamint_gb'):
                acc=agreement='N/A'
                if done and (d/'references/sealed.json').exists():
                    correct=0
                    for i in range(n):
                        pred=read(md/f'prediction_{i:04d}.json');ref=read(d/'references'/f'{c}_test'/f'{i:04d}.json')
                        assert pred['record_id']==ref['record_id'];correct+=pred['predicted_topics']==ref['topic_ids']
                    agreement=f'{100*correct/n:.2f}'
            result_rows.append(dict(corpus=c,phase='offline',method=m,
                gt='—' if m=='base' else ('✗' if m.endswith('_no_gt') else '✓'),
                acc=acc,conf=conf,predicted=s.get('n',0),updated=0,
                judged=len(quality),unknown=unknown,queue_method=q.get('method'),
                queue_stage=q.get('stage','prediction')))
            text+=f"| {m} | {acc} | {agreement} | {micro} | {macro} | {conf} | {s.get('status','queued')}; predicted {s.get('n',0)}/{n}; judged {len(quality)}/{n}; unresolved {unknown} |\n"
        write(d/'METRICS.md', '# '+NAMES[c]+' offline evaluation N=100\n\n'+text[text.rfind('## '+NAMES[c]):])
        write(d/'RESULTS.md',render([r for r in result_rows if r['corpus']==c],sup,now,STORAGE,policy,d/'METRICS.md'))
        text+=f'\n[Run details](<{d / "METRICS.md"}>).\n\n'
    if (STORAGE/'online100'/os.environ.get('EXPERIMENT_RUN_ID','run_20260913')/'policy.json').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('online100_report',ROOT/'experiments/online100/report.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        text+='\n'+m.render_online(result_rows)+'\n'
    text+='## Preserved earlier runs\n\nEarlier full-test scores use different denominators and protocols. They remain in their original directories and must not be compared as the same run.\n\n'
    for c,path in [('Superseded 24/128/8-item offline pilot','budget_pilot/run_20260913'),('Dreaddit','dreaddit_icl/comparison_run_20260912'),('GoEmotions','goemotions_offline/run_20260912'),('Paired corpora','paired_feedback/run_20260912')]:text+=f'- [{c}](<{STORAGE/path/"METRICS.md"}>)\n'
    if policy.get('offline_priority')==policy.get('online_priority')=='complete_100':
        text=text.replace('at most 2 hours of wall time per dataset, serial execution (up to about 8 hours total, plus transition overhead)', 'additional time is authorized for all scheduled offline and online N=100 evaluations and judgments; the previous two-hour cutoff is disabled')
        text=text.replace('A 2-hour deadline stops a corpus gracefully and proceeds to the next. Incomplete rows remain incomplete; the deadline does not guarantee all rows finish. A resumed corpus retains its original deadline.', 'All scheduled rows continue toward 100 predictions and judgments. Previously time-limited rows resume from saved checkpoints; no final result uses a smaller denominator.')
    elif policy.get('online_priority')=='complete_100':
        text=text.replace('at most 2 hours of wall time per dataset, serial execution (up to about 8 hours total, plus transition overhead)', 'offline is bounded by the existing per-dataset two-hour deadline; online prioritizes completion of all 100 examples, so total runtime may exceed eight hours')
        text=text.replace('A 2-hour deadline stops a corpus gracefully and proceeds to the next. Incomplete rows remain incomplete; the deadline does not guarantee all rows finish. A resumed corpus retains its original deadline.', 'The existing two-hour deadline bounds offline work. Online work continues to its authorized 100-example target. A resumed offline phase retains its original deadline.')
    if policy.get('uniform_policy'):
        first_section=text.index('## Dreaddit')
        text=('# Fresh uniform comparison: 100 shared evaluation items per dataset\n\n'
              f'Updated: {now}. Run: {policy["run_id"]}. All 24 rows begin afresh; old predictions, judgments, optimizer artifacts and playbooks are never imported. Same 400 unique evaluation IDs, fixed seed 42, Qwen3-8B Q4_K_M, thinking off, context 32768.\n\n'
              'Common initial output caps: prediction/generator/optimizer/reflector 4096; curator 8192; judge 384. Length-only retries for non-judge roles double the cap to at most 16384 and available context. Partial output is discarded. ACE/DC memories are capped at 4096 Qwen tokens; over-budget candidates retain the previous valid memory, with a logged event. These rules apply from the start to every method.\n\n'
              'Official method-specific prompts, optimizer search temperatures and reduced search budgets are preserved. Supervised offline: Base, ICL (up to 8 demos), MIPROv2 (2 candidates, 4 trials), GEPA (96 metric-call budget). GT-free offline: Base and ACE with 4 separate adaptation items. Online: DC/ACE, GT yes/no on released-label corpora and GT-free only on CaChe/ParlaMint. This is a controlled local transfer, not an exact paper reproduction.\n\n'
              'Acc: Dreaddit binary accuracy; GoEmotions exact label-set accuracy; CaChe/ParlaMint N/A. Conformability: reference-blind same-family source grounding, not human validation. Final scores require all 100 resolved judgments. No test labels or judge outcomes enter offline adaptation; online current labels arrive only after the saved prediction. Extra runtime is authorized; there is no two-hour cutoff.\n\n'
              +text[first_section:])
        text+='\n[Archived earlier N=100 results](<' + str(STORAGE/'experiment_monitor/incidents/output_cap_recovery_20260914/prior_RESULTS.md') + '>).\n'
    for p in [OFFLINE/'METRICS.md',STORAGE/'METRICS.md']:write(p,text)
    write(STORAGE/'RESULTS.md',render(result_rows,sup,now,STORAGE,policy,STORAGE/'METRICS.md',history=True))
    write(OFFLINE/'RESULTS.md',render([r for r in result_rows if r['phase']=='offline'],sup,now,STORAGE,policy,OFFLINE/'METRICS.md'))
    print(json.dumps(dict(updated_at=now,protocol='shared-evaluation100-v1',corpus=sup.get('corpus'),status=sup.get('status'),results=str(STORAGE/'RESULTS.md'))))

if __name__=='__main__':main()
