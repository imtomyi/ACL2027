import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(c):
    os.environ['PILOT_CORPUS']=c
    spec=importlib.util.spec_from_file_location('test_online_'+c,HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Contracts(unittest.TestCase):
    def test_all_corpora_same_100_ids_and_schema(self):
        for c in ['dreaddit','goemotions','cache','parlamint_gb']:
            m=load(c)
            if m.SUPERVISED:
                a,_=m.s.data();b,_=m.s.data();ids=[r['record_id'] for r in a['test']]
                self.assertEqual(ids,[r['record_id'] for r in b['test']]);self.assertEqual(len(ids),100)
                self.assertFalse(set(ids)&{r['record_id'] for r in a['train']+a['dev']})
            else:
                rows=m.g.read(ROOT/'Storage/paired_feedback/run_20260912/data'/f'{c}_test.jsonl');self.assertGreaterEqual(len(rows),100)
            with tempfile.TemporaryDirectory(dir=ROOT/'Storage/online100') as tmp:
                m.RUN=Path(tmp)
                with patch.object(m,'render',lambda:None):m.prepare();m.prepare()
                self.assertEqual(m.read(m.RUN/'data/manifest.json')['n'],100)
            self.assertEqual(len(m.METHODS),4 if m.SUPERVISED else 2);self.assertEqual(m.N,100)
            self.assertEqual(m.g.GEN_SCHEMA['properties']['selected_topics']['items']['enum'],list(m.g.TOPICS[c]))
    def test_topic_gt_free_never_annotates(self):
        for c in ['cache','parlamint_gb']:
            m=load(c)
            self.assertEqual(m.METHODS,['dc_online_no_gt','ace_online_no_gt'])
            with patch.object(m.p,'Native',side_effect=AssertionError('Annotation must not run')):
                m.prepare_references()
    def test_dc_commit_precedes_feedback_and_gt_free_is_blind(self):
        m=load('dreaddit');root=ROOT/'Storage/online100';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            dest=Path(tmp)/'prediction_0000.json';native=object.__new__(m.Native)
            native.pending_prediction=(dest,dict(record_id='internal-test',memory_before_sha256='empty'))
            native.reference={'topic_ids':['1']};output=json.dumps(dict(reasoning='test',bullet_ids=[],final_answer='test',selected_topics=['1']))
            observed=[]
            def fake(this,messages,**kw):
                observed.append((kw['role'],messages))
                if kw['role']=='curator':self.assertTrue(dest.exists())
                return output
            with patch.object(m.g.CachedNative,'chat',fake):
                native.chat([dict(role='user',content='source only')],role='prediction')
                native.chat([dict(role='user',content='update memory')],role='curator')
                native.reference=None;native.chat([dict(role='user',content='update memory')],role='curator')
            self.assertNotIn('Released dataset labels',str(observed[0]))
            self.assertIn('Released dataset labels',str(observed[1]))
            self.assertNotIn('Released dataset labels',str(observed[2]))
    def test_ace_resume_never_reapplies_committed_update(self):
        m=load('dreaddit');root=ROOT/'Storage/online100';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            m.RUN=Path(tmp);m.g.RUN=m.RUN;m.N=2
            records=[dict(record_id=str(i),text='internal test',target=[0]) for i in range(2)]
            value=dict(reasoning='test',bullet_ids=[],final_answer='test',selected_topics=['0']);raw=json.dumps(value)
            updates=[]
            def adapt(native,q,v,memory,next_id,step,ref):
                self.assertTrue((m.RUN/'ace_online_ref'/f'prediction_{step-1:04d}.json').exists())
                updates.append(step);return memory+'x',next_id+1,'accepted'
            with patch.object(m,'rows',lambda:records),patch.object(m,'Native',lambda d:None),patch.object(m.g,'generate',lambda *a:(raw,value)),patch.object(m,'adapt',adapt),patch.object(m,'render',lambda:None):
                m.run_method('ace_online_ref');m.run_method('ace_online_ref')
            self.assertEqual(updates,[1,2]);self.assertEqual(m.read(m.RUN/'ace_online_ref/state.json')['n'],2)
if __name__=='__main__':unittest.main()
