"""Internal software cases for the offline MIPROv2 runner, not experiment observations."""
from pathlib import Path
import json, tempfile, unittest
from unittest.mock import patch

import run
from core import load
from optimizer import TaskAdapter, learned_context

TASK = dict(instruction='Classify whether the author expresses stress. Select exactly one label: 0=no stress, 1=stress.',
            codebook={'0': 'no stress', '1': 'stress'}, labels=[0, 1], single_label=True)
TEXT = 'abcd efgh'
WIRE = dict(decision=dict(supported_labels=[dict(label_id=1, evidence=[dict(quote='abcd', start=0, end=4)])]),
            explanation='brief', bullet_ids=[])


class Tokenizer:
    def encode(self, text): return list(text)


class FakeNative:
    def __init__(self, failures=()):
        self.tokenizer = Tokenizer(); self.calls = []; self.failures = set(failures)
    def structured(self, messages, role, key, schema, validator):
        self.calls.append(key)
        if key.split(':format:')[0] in self.failures: raise ValueError('Format retries exhausted')
        validator(WIRE); return WIRE
    def chat(self, *a, **k): raise AssertionError('Evaluation must not call an unstructured role')


class Signature:
    instructions = TASK['instruction']


class Classifier:
    signature = Signature(); demos = []


class Program:
    classifier = Classifier()


def workspace(root, seed=42, n=3):
    parent, stage = root/'parent', root/'stage'
    (parent/'data'/'dreaddit').mkdir(parents=True)
    (parent/'tasks.json').write_text(json.dumps({'dreaddit': TASK}))
    ids = [f'dreaddit_test_{i:05d}' for i in range(n)]
    for split in ['train', 'dev', 'test']:
        (parent/'data'/'dreaddit'/f'{split}.jsonl').write_text(
            ''.join(json.dumps(dict(record_id=rid, text=TEXT, target=[1]))+'\n' for rid in ids))
    stage.mkdir()
    (stage/'orders.json').write_text(json.dumps({'dreaddit': {str(seed): {'evaluation': ids}}}))
    cell = dict(id=f'dreaddit__offline__miprov2__gt_yes__seed{seed}', dataset='dreaddit', phase='offline',
                method='miprov2', adaptation_gt='yes', seed=seed, n=n)
    return parent, stage, cell, ids


class RunnerTests(unittest.TestCase):
    def execute(self, root, native):
        parent, stage, cell, ids = workspace(root)
        with patch.object(run, 'compile_program', return_value=Program()):
            run.execute(parent, stage, cell, native)
        return parent, stage, cell, ids

    def test_frozen_program_precedes_and_stamps_every_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage, cell, ids = self.execute(root, FakeNative())
            directory = stage/'runs'/cell['id']
            frozen = load(directory/'frozen_program.json')
            predictions = [load(directory/f'prediction_{i:03d}.json') for i in range(len(ids))]
            self.assertEqual([p['record_id'] for p in predictions], ids)
            self.assertTrue(all(p['learned_context_sha256'] == frozen['learned_context_sha256'] for p in predictions))
            self.assertTrue(all(p['valid'] and p['output']['label_ids'] == [1] for p in predictions))
            self.assertEqual(load(directory/'state.json')['status'], 'prediction_complete')

    def test_resume_recommits_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage, cell, ids = self.execute(root, FakeNative())
            again = FakeNative()
            with patch.object(run, 'compile_program', return_value=Program()):
                run.execute(parent, stage, cell, again)
            self.assertEqual(again.calls, [])

    def test_exhausted_format_is_recorded_and_evaluation_continues(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage, cell, ids = workspace(root)
            native = FakeNative(failures={'evaluation:1:'+ids[1]})
            with patch.object(run, 'compile_program', return_value=Program()):
                run.execute(parent, stage, cell, native)
            directory = stage/'runs'/cell['id']
            predictions = [load(directory/f'prediction_{i:03d}.json') for i in range(len(ids))]
            self.assertEqual([p['valid'] for p in predictions], [True, False, True])
            self.assertEqual(predictions[1]['error_type'], 'exhausted_format_failure')
            self.assertEqual(load(directory/'state.json')['status'], 'prediction_complete_with_failures')

    def test_changed_committed_order_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage, cell, ids = self.execute(root, FakeNative())
            path = stage/'runs'/cell['id']/'prediction_000.json'
            record = load(path); record['record_id'] = 'dreaddit_test_09999'
            path.write_text(json.dumps(record))
            with patch.object(run, 'compile_program', return_value=Program()):
                with self.assertRaises(RuntimeError): run.execute(parent, stage, cell, FakeNative())

    def test_changed_frozen_program_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage, cell, ids = self.execute(root, FakeNative())
            path = stage/'runs'/cell['id']/'frozen_program.json'
            record = load(path); record['demos'] = record['demos']+1
            path.write_text(json.dumps(record))
            with patch.object(run, 'compile_program', return_value=Program()):
                with self.assertRaises(RuntimeError): run.execute(parent, stage, cell, FakeNative())


class Demo(dict):
    def __getattr__(self, key): return self[key]


class BudgetTests(unittest.TestCase):
    def candidate(self, demos, tokens):
        class Wide:
            instructions = 'x'*tokens
        native = FakeNative()
        with patch('optimizer.RUNTIME', (native, dict(TASK, dataset='dreaddit'), Path('.'))):
            return TaskAdapter()(None, {}, Wide(), demos, dict(passage=TEXT)), native

    def test_oversize_learned_context_is_rejected_without_model_calls(self):
        value, native = self.candidate([], 5000)
        self.assertEqual(value[0]['label_ids'], [])
        self.assertEqual(native.calls, [])

    def test_excess_demonstrations_are_rejected_without_model_calls(self):
        value, native = self.candidate([Demo(passage=TEXT, label_ids=[1])]*9, 10)
        self.assertEqual(value[0]['label_ids'], [])
        self.assertEqual(native.calls, [])

    def test_admissible_candidate_reaches_the_shared_output_contract(self):
        value, native = self.candidate([Demo(passage=TEXT, label_ids=[1])], 10)
        self.assertEqual(value[0]['label_ids'], [1])
        self.assertEqual(len(native.calls), 1)


class IsolationTests(unittest.TestCase):
    """The adapter reads module-level runtime state and DSPy settings are process-global."""

    def test_optimizer_runtime_is_module_global(self):
        import optimizer
        self.assertIn('RUNTIME', vars(optimizer))
        self.assertIn('global RUNTIME', __import__('inspect').getsource(optimizer.compile_program))

    def test_every_development_case_is_dispatched_as_its_own_process(self):
        source = (Path(__file__).parent/'stage.py').read_text()
        self.assertNotIn('ThreadPoolExecutor', source)
        self.assertIn("'--dev'", source)
        self.assertIn('start_new_session=True', source)


if __name__ == '__main__': unittest.main()
