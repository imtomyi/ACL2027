"""Internal non-production fixtures for variable train/evaluation lengths."""
from pathlib import Path
import json,tempfile,unittest
from core import atomic,load
from test_adaptation import TASK,NativeFixture,Behavior
from run import execute


class FlexibleExecution(unittest.TestCase):
    def execute_sizes(self,phase,train_n,test_n):
        Behavior.setUpClass()
        with tempfile.TemporaryDirectory() as td:
            parent=Path(td)/'parent';stage=Path(td)/'stage';stage.mkdir()
            atomic(parent/'tasks.json',{'dreaddit':TASK})
            order={}
            for split,n,role in [('train',train_n,'adaptation'),('test',test_n,'evaluation')]:
                data=[dict(record_id=f'{split}-{i}',text='x',target=[1]) for i in range(n)]
                p=parent/'data/dreaddit'/(split+'.jsonl');p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(''.join(json.dumps(r)+'\n' for r in data));order[role]=[r['record_id'] for r in data]
            atomic(stage/'orders.json',{'dreaddit':{'42':order}})
            cell=dict(id='fixture',dataset='dreaddit',phase=phase,method='ace',adaptation_gt='no',seed=42,
                      n=test_n,train_n=train_n,dev_n=6,update_n=train_n if phase=='offline' else test_n)
            execute(parent,stage,cell,NativeFixture(),Behavior.upstream)
            state=load(stage/'runs/fixture/state.json')
            self.assertEqual(state['predicted'],test_n);self.assertEqual(state['total'],test_n)
            self.assertEqual(state['updated'],cell['update_n']);self.assertEqual(state['update_total'],cell['update_n'])
            self.assertEqual(state['adapted'],train_n if phase=='offline' else 0)

    def test_offline_train_and_test_sizes_differ(self):self.execute_sizes('offline',3,7)
    def test_online_stream_size_controls_updates(self):self.execute_sizes('online',3,9)


if __name__=='__main__':unittest.main()
