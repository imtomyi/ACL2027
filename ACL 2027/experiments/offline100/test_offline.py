import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(c):
    os.environ['PILOT_CORPUS']=c
    spec=importlib.util.spec_from_file_location('offline100_test_'+c,HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class OfflineContracts(unittest.TestCase):
    def test_exactly_400_evaluation_ids_shared_with_online(self):
        total=0
        for c in ['dreaddit','goemotions','cache','parlamint_gb']:
            m=load(c);rows=m.jsonl(m.ONLINE/'data/test.jsonl');self.assertEqual(len(rows),100);self.assertEqual(len({r['record_id'] for r in rows}),100);total+=len(rows)
            if m.SUPERVISED:self.assertEqual(m.m.data()[0]['test'],rows)
            else:self.assertEqual(m.jsonl(m.OLD/'data'/f'{c}_test.jsonl'),rows[:8])
        self.assertEqual(total,400)
    def test_offline_evaluation_does_not_update_playbook(self):
        m=load('cache');root=ROOT/'Storage/offline100';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            m.RUN=Path(tmp);m.m.RUN=m.RUN;m.m.g.RUN=m.RUN;m.N=2;d=m.RUN/'cache/ace_offline_no_gt';d.mkdir(parents=True)
            m.atomic(d/'state.json',dict(n=0,adapted=4,memory='frozen test memory',next_id=2,status='running',recent_seconds=[]))
            rows=[dict(record_id=str(i),text='internal contract test') for i in range(2)]
            seen=[]
            def generate(native,q,memory):
                seen.append(memory);v=dict(reasoning='test',final_answer='test',bullet_ids=[],selected_topics=['other']);return json.dumps(v),v
            original=m.jsonl
            def data(path):return rows if path.name=='cache_test.jsonl' else []
            with patch.object(m,'jsonl',data),patch.object(m.m,'Native',lambda d:None),patch.object(m.m.g,'generate',generate),patch.object(m.m,'adapt',side_effect=AssertionError('No evaluation feedback')),patch.object(m,'render',lambda:None):m.run_topic('ace_offline_no_gt')
            self.assertEqual(seen,['frozen test memory']*2);state=m.read(d/'state.json');self.assertEqual(state['n'],2);self.assertEqual(state['memory'],'frozen test memory');self.assertEqual(state['status'],'complete')
if __name__=='__main__':unittest.main()
