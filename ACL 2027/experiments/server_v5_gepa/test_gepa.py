"""Internal software cases for the offline GEPA runner, not experiment observations."""
from pathlib import Path
import json, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
import dspy

import run
import gepa_optimizer as g
from core import load
from optimizer import learned_context

TASK = dict(instruction='Classify whether the author expresses stress. Select exactly one label: 0=no stress, 1=stress.',
            codebook={'0': 'no stress', '1': 'stress'}, labels=[0, 1], single_label=True, dataset='dreaddit')
EMOTION = dict(instruction='emotions', codebook={'1': 'a', '2': 'b', '3': 'c'}, labels=[1, 2, 3],
               single_label=False, dataset='goemotions')
TEXT = 'abcd efgh'
WIRE = dict(decision=dict(supported_labels=[dict(label_id=1, evidence=[dict(quote='abcd', start=0, end=4)])]),
            explanation='brief', bullet_ids=[])


class Tokenizer:
    def encode(self, text): return list(text)


class FakeNative:
    def __init__(self): self.tokenizer = Tokenizer(); self.calls = []
    def structured(self, messages, role, key, schema, validator):
        self.calls.append(key); validator(WIRE); return WIRE


def candidate(instruction):
    return SimpleNamespace(classifier=SimpleNamespace(signature=SimpleNamespace(instructions=instruction), demos=[]))


def results(instructions, means):
    return SimpleNamespace(candidates=[candidate(i) for i in instructions], val_aggregate_scores=means,
                           discovery_eval_counts=[0]*len(instructions), best_idx=max(range(len(means)), key=means.__getitem__))


class MetricTests(unittest.TestCase):
    def metric(self, gold, predicted, task=EMOTION):
        with tempfile.TemporaryDirectory() as temp:
            return g.feedback_metric(task, Path(temp))(dspy.Example(label_ids=gold), dspy.Prediction(label_ids=predicted))

    def test_item_score_is_set_f1_and_exact_for_single_label(self):
        self.assertEqual(self.metric([1], [1], TASK).score, 1.0)
        self.assertEqual(self.metric([1], [0], TASK).score, 0.0)
        self.assertAlmostEqual(self.metric([1, 2], [2, 3]).score, 0.5)

    def test_feedback_names_reference_missed_and_unsupported_labels(self):
        text = self.metric([1, 2], [2, 3]).feedback
        self.assertIn('Reference labels', text); self.assertIn('Missed: [\'1=a\']', text); self.assertIn('Unsupported by the reference: [\'3=c\']', text)

    def test_invalid_output_scores_zero_with_feedback(self):
        value = self.metric([1], [])
        self.assertEqual(value.score, 0.0); self.assertIn('invalid', value.feedback)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); g.LEDGER = g.Ledger(Path(self.temp.name)/'ledger.jsonl')
        self.gold = [0]*8 + [1]*2
        self.development = [dict(text=f'item {i}', target=[y]) for i, y in enumerate(self.gold)]
    def tearDown(self): self.temp.cleanup()
    def record(self, instruction, labels):
        for row, label in zip(self.development, labels):
            if label is not None: g.LEDGER.record(learned_context(candidate(instruction).classifier.signature, []), row['text'], label)

    def test_corpus_objective_overrides_disagreeing_gepa_mean(self):
        # A: majority class, item accuracy 0.8, macro-F1 0.44. B: accuracy 0.7, macro-F1 0.67.
        self.record('A', [[0]]*10)
        self.record('B', [[0]]*5 + [[1]]*3 + [[1]]*2)
        best, rows = g.select(results(['A', 'B'], [0.8, 0.7]), self.development, TASK, FakeNative())
        self.assertEqual(best['index'], 1)
        self.assertGreater(rows[1]['corpus_objective'], rows[0]['corpus_objective'])

    def test_incomplete_candidate_is_ineligible(self):
        self.record('A', [[0]]*10)
        self.record('B', [[l] for l in self.gold[:9]] + [None])
        best, rows = g.select(results(['A', 'B'], [0.8, 1.0]), self.development, TASK, FakeNative())
        self.assertEqual(best['index'], 0); self.assertIsNone(rows[1]['corpus_objective'])

    def test_any_invalid_development_prediction_scores_zero(self):
        self.record('A', [[0]]*10)
        self.record('B', [[l] for l in self.gold[:9]] + [[]])
        best, rows = g.select(results(['A', 'B'], [0.8, 0.9]), self.development, TASK, FakeNative())
        self.assertEqual(rows[1]['corpus_objective'], 0.0); self.assertEqual(best['index'], 0)

    def test_ties_prefer_gepa_mean_then_earlier_candidate(self):
        for name in ['A', 'B', 'C']: self.record(name, [[0]]*10)
        best, _ = g.select(results(['A', 'B', 'C'], [0.5, 0.8, 0.8]), self.development, TASK, FakeNative())
        self.assertEqual(best['index'], 1)

    def test_ledger_persists_and_rejects_changed_predictions(self):
        g.LEDGER.record('ctx', 'passage', [1])
        reloaded = g.Ledger(Path(self.temp.name)/'ledger.jsonl')
        self.assertEqual(reloaded.get('ctx', 'passage'), [1])
        with self.assertRaises(RuntimeError): reloaded.record('ctx', 'passage', [0])


class BudgetTests(unittest.TestCase):
    def compile(self, probe):
        captured = {}
        class FakeGEPA:
            def __init__(self, **kwargs): captured.update(kwargs)
            def compile(self, program, trainset, valset):
                captured.update(train_n=len(trainset), development_n=len(valset))
                return SimpleNamespace(detailed_results=SimpleNamespace(candidates=[program], val_aggregate_scores=[1.0],
                    discovery_eval_counts=[0], best_idx=0, total_metric_calls=captured['max_metric_calls'], num_full_val_evals=1))
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); development = [dict(text=f'd{i}', target=[1]) for i in range(3)]
            seed = g.Program(TASK['instruction'])
            context = learned_context(seed.classifier.signature, seed.classifier.demos)
            with (directory/'prediction_ledger.jsonl').open('w') as f:
                for r in development:
                    f.write(json.dumps(dict(context_sha256=g.sha(context), passage_sha256=g.sha(r['text']), label_ids=[1]))+'\n')
            with patch.object(g.dspy, 'GEPA', FakeGEPA):
                g.compile_program(FakeNative(), TASK, [dict(text='t', target=[0])], development, directory, 43, probe=probe)
            optimization = load(directory/'optimization.json')
        return captured, optimization

    def test_design_budget_maps_to_the_pinned_api(self):
        captured, optimization = self.compile(False)
        self.assertEqual(captured['max_metric_calls'], 3000)
        self.assertEqual(captured['reflection_minibatch_size'], 3)
        self.assertEqual(captured['num_threads'], 1); self.assertEqual(captured['seed'], 43)
        self.assertTrue(captured['track_stats']); self.assertNotIn('auto', captured)
        self.assertEqual(captured['reflection_lm'].kwargs['temperature'], 1.0)
        self.assertEqual(optimization['status'], 'complete'); self.assertEqual(optimization['selected_index'], 0)
        self.assertEqual(optimization['objective'], 'macro_f1')

    def test_probe_uses_the_small_development_budget(self):
        captured, _ = self.compile(True)
        self.assertEqual(captured['max_metric_calls'], 30)


class RunnerTests(unittest.TestCase):
    def test_evaluation_uses_the_frozen_selected_program(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent, stage = root/'parent', root/'stage'
            (parent/'data'/'dreaddit').mkdir(parents=True); stage.mkdir()
            (parent/'tasks.json').write_text(json.dumps({'dreaddit': {k: v for k, v in TASK.items() if k != 'dataset'}}))
            ids = [f'dreaddit_test_{i:05d}' for i in range(3)]
            for split in ['train', 'dev', 'test']:
                (parent/'data'/'dreaddit'/f'{split}.jsonl').write_text(''.join(json.dumps(dict(record_id=r, text=TEXT, target=[1]))+'\n' for r in ids))
            (stage/'orders.json').write_text(json.dumps({'dreaddit': {'42': {'evaluation': ids}}}))
            cell = dict(id='dreaddit__offline__gepa__gt_yes__seed42', dataset='dreaddit', phase='offline', method='gepa',
                        adaptation_gt='yes', seed=42, n=3)
            with patch.object(run, 'compile_program', return_value=candidate(TASK['instruction'])):
                run.execute(parent, stage, cell, FakeNative())
            d = stage/'runs'/cell['id']; frozen = load(d/'frozen_program.json')
            predictions = [load(d/f'prediction_{i:03d}.json') for i in range(3)]
            self.assertEqual([p['record_id'] for p in predictions], ids)
            self.assertTrue(all(p['learned_context_sha256'] == frozen['learned_context_sha256'] for p in predictions))
            self.assertEqual(load(d/'state.json')['status'], 'prediction_complete')


class IsolationTests(unittest.TestCase):
    def test_every_development_case_is_dispatched_as_its_own_process(self):
        source = (Path(__file__).parent/'stage.py').read_text()
        self.assertNotIn('ThreadPoolExecutor', source); self.assertIn("'--dev'", source)

    def test_pinned_optimizer_modules_are_importable(self):
        import stage
        pins = stage.optimizer_pins()
        self.assertIn('gepa', pins); self.assertEqual(len(pins['module_sha256']), 5)


if __name__ == '__main__': unittest.main()
