"""Internal software fixtures only; never scientific observations."""
import json, unittest
from rubric import DIMENSIONS, messages, validate, decision

class RubricTests(unittest.TestCase):
    def output(self): return dict(label_ids=[0],explanation='description',evidence=[dict(label_id=0,quote='x',start=0,end=1)],bullet_ids=['private-bullet'])
    def rating(self, **changes): return dict(dimensions=dict({k:2 for k in DIMENSIONS},**changes),rationale='brief justification')
    def test_blinding(self):
        task=dict(instruction='task',codebook={'0':'label'},target='secret',method='secret',memory='secret')
        payload=json.loads(messages(task,'x',self.output())[1]['content'])
        self.assertEqual(set(payload),{'task','codebook','source','answer'})
        self.assertEqual(set(payload['answer']),{'label_ids','explanation','evidence'})
        self.assertNotIn('private-bullet',json.dumps(payload))
    def test_all_four_dimensions_required(self):
        self.assertTrue(decision(self.rating(),self.output())['pass'])
        for d in DIMENSIONS:self.assertFalse(decision(self.rating(**{d:1}),self.output())['pass'])
    def test_unknown_is_not_failure_or_pass(self):
        self.assertIsNone(decision(self.rating(attribution=None),self.output())['pass'])
        self.assertFalse(decision(self.rating(attribution=None,factual_support=0),self.output())['pass'])
    def test_missing_evidence_known_failure(self):
        output=self.output();output['evidence']=[]
        self.assertFalse(decision(self.rating(),output)['pass'])
    def test_booleans_and_extra_fields_rejected(self):
        with self.assertRaises(ValueError):validate(self.rating(factual_support=True))
        v=self.rating();v['pass']=True
        with self.assertRaises(ValueError):validate(v)

class RuntimeTests(unittest.TestCase):
    def test_lazy_imports_resolve_before_preflight_threads(self):
        # Concurrent first imports of transformers.AutoTokenizer raise ImportError.
        from pathlib import Path
        source=(Path(__file__).parent/'evaluate.py').read_text()
        body=source[source.index('def preflight'):source.index('def seal')]
        self.assertLess(body.index('from transformers import AutoTokenizer'),body.index('ThreadPoolExecutor'))

class AllocationTests(unittest.TestCase):
    def test_gpus_with_foreign_processes_are_excluded_not_shared(self):
        import evaluate
        services=[dict(gpu=g,uuid=f'U{g}',port=11840+g) for g in range(4)]
        listing='U0, 10\nU1, 11\nU2, 12\nU3, 13\nOTHER, 14'
        def environ(pid):
            if pid==10:return [b'OLLAMA_HOST=127.0.0.1:11840']
            if pid==11:return [b'OLLAMA_HOST=127.0.0.1:19999']
            if pid==12:raise PermissionError()
            raise FileNotFoundError()
        clean,excluded=evaluate.clean_services(services,listing,environ)
        self.assertEqual([s['gpu'] for s in clean],[0,3]);self.assertEqual(excluded,[1,2])


class CohortTests(unittest.TestCase):
    def test_cohort_spec_selects_only_its_named_prediction_stages(self):
        import tempfile
        from pathlib import Path
        from core import atomic, digest
        import evaluate
        with tempfile.TemporaryDirectory() as temp:
            parent,stage=Path(temp)/'parent',Path(temp)/'stage';ids=[f'd{i:03d}' for i in range(100)]
            (parent/'data'/'dreaddit').mkdir(parents=True)
            (parent/'data'/'dreaddit'/'test.jsonl').write_text(''.join(json.dumps(dict(record_id=r,text='x'))+'\n' for r in ids))
            source=parent/'stages'/'optimizer'
            cell=dict(id='dreaddit__offline__miprov2__gt_yes__seed42',dataset='dreaddit',phase='offline',method='miprov2',adaptation_gt='yes',seed=42,n=100)
            for i,r in enumerate(ids):atomic(source/'runs'/cell['id']/f'prediction_{i:03d}.json',dict(record_id=r,index=i))
            atomic(source/'runs'/cell['id']/'state.json',dict(status='prediction_complete',attempted=100))
            manifest=dict(cells=[cell],admitted_cells=[cell],files={});manifest['seal_sha256']=digest(manifest)
            atomic(source/'manifest.json',manifest)
            atomic(stage/'cohort.json',dict(sources=[['stages/optimizer','miprov2']],expected_runs=1,precursor='stages/optimizer/queue.json'))
            cells=evaluate.inventory(parent,stage)
            self.assertEqual([c['cell']['id'] for c in cells],[cell['id']]);self.assertEqual(len(cells[0]['predictions']),100)
            atomic(stage/'cohort.json',dict(sources=[['stages/optimizer','miprov2']],expected_runs=2,precursor='stages/optimizer/queue.json'))
            with self.assertRaises(RuntimeError):evaluate.inventory(parent,stage)

if __name__=='__main__':unittest.main()
