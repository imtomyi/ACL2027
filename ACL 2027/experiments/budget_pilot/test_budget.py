import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent

def load(name,corpus):
    with patch.dict(os.environ,{'PILOT_CORPUS':corpus}):
        spec=importlib.util.spec_from_file_location(name+corpus,HERE/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class BudgetTests(unittest.TestCase):
    def test_real_supervised_sampling(self):
        for c,n in [('goemotions',128),('dreaddit',24)]:
            m=load('supervised',c);a,_=m.data();b,_=m.data()
            self.assertEqual(a,b);self.assertEqual(len(a['test']),n);self.assertEqual(len(a['train']),32)
            ids={k:{r['record_id'] for r in v} for k,v in a.items()}
            for x,y in [('train','dev'),('train','test'),('dev','test')]:self.assertFalse(ids[x]&ids[y])
            for rows in a.values():
                for row in rows:self.assertEqual(m.parse_labels(row['target']),row['target'])
    def test_metrics_use_dynamic_label_count(self):
        for c,label in [('goemotions',27),('dreaddit',1)]:
            m=load('supervised',c);s=m.score([dict(prediction=[label],target=[label]),dict(prediction=None,target=[label])])
            self.assertEqual(s['acc'],0.5);self.assertAlmostEqual(s['micro_f1'],2/3);self.assertAlmostEqual(s['macro_f1'],(2/3)/len(m.LABELS))
    def test_judge_and_online_commit(self):
        m=load('supervised','dreaddit')
        class Fake:
            def __init__(self,*a):pass
            def chat(self,*a,**k):self.last_usage={};return '{}'
        with tempfile.TemporaryDirectory() as temp:
            m.RUN=Path(temp);m.N=1;d=m.RUN/'base';d.mkdir()
            response='internal unit test placeholder';m.append(d/'predictions.jsonl',dict(record_id='unit',response=response))
            with patch.object(m,'Native',Fake),patch.object(m,'decide',lambda x:False),patch.object(m,'render'):
                m.audit('base',{'test':[dict(record_id='unit',text='internal unit test')]})
            q=json.loads((d/'quality_state.json').read_text());self.assertEqual(q['n'],1);self.assertEqual(q['failed'],1);self.assertEqual(q['unresolved'],0)
            d=m.RUN/'dc_gt';d.mkdir();item=dict(record_id='unit',prediction=[1],target=[1],response=response,seconds=1)
            m.atomic(d/'online_state.json',dict(items=[item],memory='saved memory'))
            m.evaluate('dc_gt',{'test':[dict(record_id='unit',target=[1])]})
            self.assertEqual(json.loads((d/'state.json').read_text())['status'],'complete')
            self.assertEqual(json.loads((d/'memory.json').read_text())['memory'],'saved memory')
    def test_optimizer_budgets(self):
        m=load('supervised','goemotions');seen={}
        class Program:
            def save(self,*a):pass
        class Optimizer:
            def __init__(self,**kw):seen['init']=kw
            def compile(self,*a,**kw):seen['compile']=kw;return Program()
        with tempfile.TemporaryDirectory() as t,patch.object(m,'LocalLM',lambda *a,**kw:object()),patch.object(m.dspy,'configure'),patch.object(m.dspy,'MIPROv2',Optimizer),patch.object(m.dspy,'GEPA',Optimizer):
            rows={'train':[],'dev':[]}
            for method in ['miprov2','gepa']:
                m.compile_predictor(method,None,rows,Path(t))
                self.assertIsNone(seen['init']['auto'])
                if method=='miprov2':self.assertEqual(seen['compile']['num_trials'],4);self.assertFalse(seen['compile']['minibatch'])
                else:self.assertEqual(seen['init']['max_metric_calls'],96)
    def test_paired_isolated(self):
        for c in ['cache','parlamint_gb']:
            m=load('paired',c);self.assertEqual(list(m.g.TOPICS),[c]);self.assertEqual(len(m.METHODS),7)

if __name__=='__main__':unittest.main()
