"""Keep existing reduced offline tasks; move every online row to the N=100 queue."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
ROOT=Path(__file__).resolve().parents[2]
c=os.environ['PILOT_CORPUS'];path=ROOT/'experiments/budget_pilot'/('supervised.py' if c in ('dreaddit','goemotions') else 'paired.py')
spec=importlib.util.spec_from_file_location('offline_only',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.METHODS=['base','icl','miprov2','gepa'] if c in ('dreaddit','goemotions') else ['base','ace_offline_no_gt']
if c in ('dreaddit','goemotions'):m.NAMES=['Qwen3-8B','ICL','MIPROv2','GEPA']
else:
    m.g.METHODS=m.METHODS
    m.prepare_references=lambda:None
    def render_gt_free():
        import subprocess
        lines=['# '+c+' reduced GT-free offline pilot','','User selected GT-free only. No reference annotation is generated or supplied. ACC and reference agreement are N/A. Conformability is a source-grounding LLM judgment. Offline adapt N=4, test N=8; online runs separately on N=100.','','| Method | GT | ACC | Conformability % | Progress |','| --- | --- | --- | ---: | --- |']
        for method in m.METHODS:
            d=m.RUN/c/method;p=d/'state.json';state=json.loads(p.read_text()) if p.exists() else {};quality=m.g.read(d/'quality.jsonl')
            unknown=sum(x.get('decision') is None for x in quality)
            conf=f'{100*sum(x.get("decision") is True for x in quality)/8:.2f}' if len(quality)==8 and not unknown else '—'
            lines.append(f'| {method} | {"—" if method=="base" else "✗"} | N/A | {conf} | {state.get("status","queued")}; predicted {state.get("n",0)}/8; judged {len(quality)}/8; unresolved {unknown} |')
        (m.RUN/'METRICS.md').write_text('\n'.join(lines)+'\n')
        if not (m.RUN/'RESULTS.md').exists():(m.RUN/'RESULTS.md').symlink_to('METRICS.md')
        subprocess.run([sys.executable,str(ROOT/'experiments/reporting/update_results.py')],check=True,stdout=subprocess.DEVNULL)
    m.render=render_gt_free
m.RUN.mkdir(parents=True,exist_ok=True)
config=dict(methods=m.METHODS,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),online='separate online100-v1; all 100 per method')
p=m.RUN/'offline_only.json'
if p.exists():assert json.loads(p.read_text())==config
else:p.write_text(json.dumps(config,indent=2)+'\n')
if __name__=='__main__':
    if '--prepare-only' in sys.argv:
        if c in ('dreaddit','goemotions'):m.freeze(*m.data())
        else:m.freeze()
        m.render()
    else:m.main()
