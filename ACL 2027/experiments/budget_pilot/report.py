"""Report actual reduced-run denominators; keep historical full-run results separate."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,os
ROOT=Path(__file__).resolve().parents[2];STORAGE=ROOT/'Storage';RUN=STORAGE/'budget_pilot/run_20260913'
N={'goemotions':128,'dreaddit':24,'cache':8,'parlamint_gb':8}
NAMES={'goemotions':'GoEmotions','dreaddit':'Dreaddit','cache':'CaChe','parlamint_gb':'ParlaMint-GB'}

def read(p):return json.loads(p.read_text()) if p.exists() else {}
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def write(p,t):
    tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(t);tmp.replace(p)

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds');sup=read(RUN/'supervisor.json')
    text=f'# Reduced four-dataset pilot\n\nUpdated: {now}. User-authorized new protocol: at most 2 hours of wall time per dataset, serial execution (up to about 8 hours total, plus transition overhead).\n\n'
    text+='Model: Qwen3-8B Q4_K_M, thinking off, seed 42. No full-run scores or predictions are imported. Fixed outcome-blind subsets are used for every method in each dataset. Small pilot results have high sampling uncertainty and are not full-test benchmarks.\n\n'
    text+='Supervised offline: Base, 8-example ICL, MIPROv2 (2 candidates, 4 trials), GEPA (96 metric-call budget). Dreaddit additionally runs DC GT yes/no. CaChe and ParlaMint run Base, ACE offline GT yes/no, DC online GT yes/no, ACE online GT yes/no using the existing provisional task. GPT-5 and supervised ACE remain outside these queues; ICL/MIPROv2/GEPA are not implemented for the provisional corpora.\n\n'
    text+='GT yes on CaChe/ParlaMint means unverified model pseudo-labels (†), never human GT. Their human-GT Acc is N/A; reference agreement is separately named. Conformability is a reference-blind same-family LLM grounding judgment, not human verification. Unresolved judgments remain unknown. Offline test labels never feed adaptation; online feedback follows the current prediction.\n\n'
    text+='A 2-hour deadline stops a corpus gracefully and proceeds to the next. Incomplete rows remain incomplete; the deadline does not guarantee all rows finish. A resumed corpus retains its original deadline.\n\n'
    for c in ['dreaddit','goemotions','cache','parlamint_gb']:
        d=RUN/c;n=N[c];entry=sup.get('corpora',{}).get(c,{});q=read(d/'queue.json')
        text+=f"## {NAMES[c]}\n\nTest N={n}. Queue: {entry.get('status','queued')}; {q.get('method','—')} / {q.get('stage','—')} {q.get('n',0)}/{q.get('total',n)}.\n\n"
        if entry.get('deadline') and entry.get('status')=='running':
            deadline=datetime.fromtimestamp(entry['deadline'],ZoneInfo('Asia/Seoul')).strftime('%H:%M:%S KST');text+=f'Wall-time deadline: {deadline}.\n\n'
        methods=['base','icl','miprov2','gepa']+(['dc_gt','dc_no_gt'] if c=='dreaddit' else []) if c in ('goemotions','dreaddit') else ['base','ace_offline_no_gt','ace_offline_ref','dc_online_no_gt','dc_online_ref','ace_online_no_gt','ace_online_ref']
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
                acc='N/A'
                if done and (d/'references/sealed.json').exists():
                    correct=0
                    for i in range(n):
                        pred=read(md/f'prediction_{i:04d}.json');ref=read(d/'references'/f'{c}_test'/f'{i:04d}.json')
                        assert pred['record_id']==ref['record_id'];correct+=pred['predicted_topics']==ref['topic_ids']
                    agreement=f'{100*correct/n:.2f}'
            text+=f"| {m} | {acc} | {agreement} | {micro} | {macro} | {conf} | {s.get('status','queued')}; predicted {s.get('n',0)}/{n}; judged {len(quality)}/{n}; unresolved {unknown} |\n"
        text+=f'\n[Run details](<{d / "METRICS.md"}>).\n\n'
    text+='## Preserved earlier runs\n\nEarlier full-test scores use different denominators and protocols. They remain in their original directories and must not be compared as the same run.\n\n'
    for c,path in [('Dreaddit','dreaddit_icl/comparison_run_20260912'),('GoEmotions','goemotions_offline/run_20260912'),('Paired corpora','paired_feedback/run_20260912')]:text+=f'- [{c}](<{STORAGE/path/"METRICS.md"}>)\n'
    for p in [RUN/'RESULTS.md',RUN/'METRICS.md',STORAGE/'RESULTS.md',STORAGE/'METRICS.md']:write(p,text)
    print(json.dumps(dict(updated_at=now,protocol='budget-pilot-v1',corpus=sup.get('corpus'),status=sup.get('status'),results=str(STORAGE/'RESULTS.md'))))

if __name__=='__main__':main()
