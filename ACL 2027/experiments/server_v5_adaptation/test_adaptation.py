"""Internal software fixtures only; never experimental or manuscript evidence."""
from pathlib import Path
import json, os, tempfile, unittest
from unittest.mock import patch
from core import atomic, load, output_schema
from adapters import ACE, DC, EMPTY, Upstream, bounded, complete_cheatsheet
from run import execute

TASK = {'instruction': 'Classify the supplied software-test string.', 'codebook': {'1': 'fixture'}, 'labels': [1], 'single_label': True}
OUTPUT = {'label_ids': [1], 'explanation': 'Software fixture.', 'bullet_ids': [],
          'evidence': [{'label_id': 1, 'quote': 'x', 'start': 0, 'end': 1}]}


class Tokenizer:
    def encode(self, text): return list(text)


class NativeFixture:
    def __init__(self):
        self.tokenizer = Tokenizer(); self.calls = []; self.ops = []; self.tags = []; self.bad_dc = False; self.interrupt_once = False
    def structured(self, messages, role, key, schema, validator):
        self.calls.append((role, key, messages))
        if role == 'generator': value = json.loads(json.dumps(OUTPUT))
        elif role == 'reflector':
            value = {k: 'Internal test' for k in ['reasoning', 'error_identification', 'root_cause_analysis', 'correct_approach', 'key_insight']}
            value['bullet_tags'] = self.tags
        else:
            if self.interrupt_once:
                self.interrupt_once = False
                raise KeyboardInterrupt()
            value = {'reasoning': 'Internal test', 'operations': self.ops}
        validator(value)
        return value
    def chat(self, messages, role, key, **kwargs):
        self.calls.append((role, key, messages))
        return '<cheatsheet>Incomplete' if self.bad_dc else '<cheatsheet>Valid test memory.</cheatsheet>'


class Behavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.upstream = Upstream(Path(os.environ['ADAPTATION_UPSTREAM']))

    def test_ace_add_ids_and_counters(self):
        n = NativeFixture(); n.ops = [{'type': 'ADD', 'section': 'OTHERS', 'content': 'Test insight.'}]
        a = ACE(n, self.upstream, TASK)
        first = a.update({'text': 'x'}, OUTPUT, EMPTY, 1, 1, 2, [1], 'first')
        self.assertIn('[misc-00001]', first['memory']); self.assertEqual(first['next_id'], 2)
        n.ops = []; n.tags = [{'id': 'misc-00001', 'tag': 'helpful'}]
        second = a.update({'text': 'x'}, OUTPUT, first['memory'], 2, 2, 2, None, 'second')
        self.assertIn('helpful=1 harmful=0', second['memory']); self.assertEqual(second['next_id'], 2)
        self.assertNotIn('**Ground Truth Answer:**', n.calls[-2][2][0]['content'])

    def test_memory_budget_rejects_without_trimming_or_consuming_ids(self):
        v = bounded(NativeFixture(), 'previous', 'x'*4097, 4, 5)
        self.assertEqual(v['memory'], 'previous'); self.assertEqual(v['next_id'], 4)
        self.assertFalse(v['accepted']); self.assertEqual(v['candidate_tokens'], 4097)

    def test_dc_commits_before_reference_and_reuses_committed_prediction(self):
        n = NativeFixture(); d = DC(n, self.upstream, TASK); events = []
        def commit(value): events.append('commit')
        def reveal():
            self.assertEqual(events, ['commit']); events.append('reveal'); return [1]
        result = d.step({'text': 'x'}, '(empty)', 1, 'one', None, commit, reveal)
        self.assertTrue(result['accepted']); self.assertEqual(events, ['commit', 'reveal'])
        self.assertEqual([c[0] for c in n.calls], ['generator', 'curator'])
        n.calls = []
        d.step({'text': 'x'}, '(empty)', 1, 'resume', OUTPUT,
               lambda v: self.fail('Duplicate prediction'), lambda: None)
        self.assertEqual([c[0] for c in n.calls], ['curator'])

    def test_dc_invalid_wrapper_exhausts_instead_of_retaining(self):
        n = NativeFixture(); n.bad_dc = True
        with self.assertRaisesRegex(ValueError, 'Format retries exhausted'):
            DC(n, self.upstream, TASK).step({'text': 'x'}, 'previous', 1, 'bad', OUTPUT, lambda v: None, lambda: None)
        self.assertEqual(len(n.calls), 2)
        with self.assertRaises(ValueError): complete_cheatsheet('<cheatsheet>x</cheatsheet><cheatsheet>y</cheatsheet>')

    def fixture(self, root, phase='online', gt='yes'):
        parent, stage = root/'parent', root/'stage'; stage.mkdir()
        atomic(parent/'tasks.json', {'dreaddit': TASK})
        path = parent/'data/dreaddit/dev.jsonl'; path.parent.mkdir(parents=True)
        path.write_text('\n'.join(json.dumps(dict(record_id=str(i), text='x'*(i+1), target=[1])) for i in range(2)))
        cell = dict(id='internal_fixture', dataset='dreaddit', phase=phase, method='ace', adaptation_gt=gt, seed=42)
        return parent, stage, cell

    def test_offline_freeze_and_resume_apply_updates_exactly_once(self):
        with tempfile.TemporaryDirectory() as temp:
            parent, stage, cell = self.fixture(Path(temp), 'offline'); n = NativeFixture()
            n.ops = [{'type': 'ADD', 'section': 'OTHERS', 'content': 'Test.'}]
            execute(parent, stage, cell, n, self.upstream, dev=True)
            d = stage/'preflight'/cell['id']; frozen = load(d/'frozen_playbook.json')
            self.assertEqual(frozen['next_id'], 3); self.assertEqual(load(d/'state.json')['updated'], 2)
            before = len(n.calls)
            execute(parent, stage, cell, n, self.upstream, dev=True)
            self.assertEqual(len(n.calls), before); self.assertEqual(load(d/'frozen_playbook.json'), frozen)

    def test_online_pause_after_prediction_resumes_update_without_regeneration(self):
        with tempfile.TemporaryDirectory() as temp:
            parent, stage, cell = self.fixture(Path(temp)); n = NativeFixture(); n.interrupt_once = True
            with self.assertRaises(KeyboardInterrupt): execute(parent, stage, cell, n, self.upstream, dev=True)
            d = stage/'preflight'/cell['id']; first = load(d/'prediction_000.json')
            self.assertEqual(len(list((d/'updates').glob('*.json'))), 0)
            execute(parent, stage, cell, n, self.upstream, dev=True)
            self.assertEqual(load(d/'prediction_000.json'), first)
            self.assertEqual(sum(c[0] == 'generator' for c in n.calls), 2)
            self.assertEqual(load(d/'state.json')['updated'], 2)
            for receipt in (d/'feedback_receipts').glob('*.json'):
                v = load(receipt); self.assertLessEqual(v['committed_at'], v['revealed_at'])

    def test_gt_no_never_opens_reference_accessor(self):
        with tempfile.TemporaryDirectory() as temp:
            parent, stage, cell = self.fixture(Path(temp), gt='no')
            with patch('run.reference_for', side_effect=AssertionError('GT leak')):
                execute(parent, stage, cell, NativeFixture(), self.upstream, dev=True)


if __name__ == '__main__': unittest.main()
