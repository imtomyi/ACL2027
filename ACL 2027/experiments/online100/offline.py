"""Keep existing reduced offline tasks; move every online row to the N=100 queue."""
from pathlib import Path
import hashlib,importlib.util,json,os
ROOT=Path(__file__).resolve().parents[2]
c=os.environ['PILOT_CORPUS'];path=ROOT/'experiments/budget_pilot'/('supervised.py' if c in ('dreaddit','goemotions') else 'paired.py')
spec=importlib.util.spec_from_file_location('offline_only',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.METHODS=['base','icl','miprov2','gepa'] if c in ('dreaddit','goemotions') else ['base','ace_offline_no_gt','ace_offline_ref']
if c in ('dreaddit','goemotions'):m.NAMES=['Qwen3-8B','ICL','MIPROv2','GEPA']
else:m.g.METHODS=m.METHODS
m.RUN.mkdir(parents=True,exist_ok=True)
config=dict(methods=m.METHODS,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),online='separate online100-v1; all 100 per method')
p=m.RUN/'offline_only.json'
if p.exists():assert json.loads(p.read_text())==config
else:p.write_text(json.dumps(config,indent=2)+'\n')
if __name__=='__main__':m.main()
