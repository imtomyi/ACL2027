import copy
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

import run as app
from test_run import task, artifact


def operation(kind='ADD', target='', replacement=''):
    return {'operation': kind, 'target_id': target, 'replacement_id': replacement,
            'feedback_ids': ['F1'], 'condition': 'Evidence attribution is ambiguous',
            'action': 'Preserve speaker boundaries when checking an interpretation',
            'exception': 'Retain uncertainty if surrounding context is unavailable'}


def approve(memory, proposal):
    return {'status': 'complete', 'memory_sha256': app.digest(memory), 'proposal_sha256': app.digest(proposal),
            'decisions': [{'proposal_id': i, **{k: True for k in app.GUARD_CRITERIA}, 'reason': 'Test only'}
                          for i in range(len(proposal['operations']))]}


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.memory = app.read(Path(__file__).with_name('seed_playbook.json'))
        self.feedback = [{'feedback_id': 'F1', 'eligible': True}]

    def apply(self, operations, guard=True, **kwargs):
        proposal = {'lesson': 'A procedure', 'operations': operations}
        g = approve(self.memory, proposal) if guard is True else guard
        return app.apply_delta(self.memory, proposal, self.feedback, 2, app.BASE_CONFIG, guard=g, **kwargs)

    def add_learned(self, name='learned-001-0'):
        self.memory['bullets'].append({'id': name, 'active': True, 'provenance': 'model_feedback',
                                     'content': {'condition': 'Case boundaries', 'action': 'Keep contexts separate', 'exception': 'Explicit shared context'}})

    def test_every_seed_protected_even_with_guard_approval(self):
        original = copy.deepcopy(self.memory)
        for seed in self.memory['bullets']:
            for kind in ['REVISE', 'DEPRECATE']:
                updated, accepted, rejected = self.apply([operation(kind, seed['id'])])
                self.assertFalse(accepted)
                self.assertIn('protected_seed_rule', rejected[0]['reasons'])
                self.assertEqual(updated, original)
        self.assertEqual(self.memory, original)

    def test_seed_only_schema_permits_add_but_not_revise_or_deprecate(self):
        validator = app.Draft202012Validator(app.updater_schema(self.memory, self.feedback))
        self.assertTrue(validator.is_valid({'lesson': 'L', 'operations': [operation()]}))
        self.assertFalse(validator.is_valid({'lesson': 'L', 'operations': [operation('DEPRECATE', 'seed-dreaddit')]}))

    def test_missing_stale_duplicate_or_negative_guard_is_held(self):
        op = operation()
        proposal = {'lesson': 'A procedure', 'operations': [op]}
        valid = approve(self.memory, proposal)
        stale = {**valid, 'memory_sha256': 'wrong'}
        duplicate = {**valid, 'decisions': valid['decisions'] * 2}
        negative = copy.deepcopy(valid)
        negative['decisions'][0]['target_fit'] = False
        for guard in [None, stale, duplicate, negative]:
            updated, accepted, _ = self.apply([op], guard=guard)
            self.assertFalse(accepted)
            self.assertEqual(updated, self.memory)

    def test_case_identifiers_cannot_become_procedures(self):
        for phrase in ['Remove stress-004', 'Reinterpret C1', 'Use person-493 evidence']:
            op = operation()
            op['action'] = phrase
            _, accepted, rejected = self.apply([op], forbidden_ids=['C1', 'person-493'])
            self.assertFalse(accepted)
            self.assertIn('identifier_leakage', rejected[0]['reasons'])

    def test_conflicting_operations_are_all_held(self):
        self.add_learned()
        ops = [operation('REVISE', 'learned-001-0'), operation('DEPRECATE', 'learned-001-0')]
        updated, accepted, rejected = self.apply(ops)
        self.assertFalse(accepted)
        self.assertEqual(updated, self.memory)
        self.assertTrue(all('conflicting_target_operations' in r['reasons'] for r in rejected))

    def test_deprecation_requires_unchanged_learned_replacement(self):
        self.add_learned()
        _, accepted, rejected = self.apply([operation('DEPRECATE', 'learned-001-0')])
        self.assertFalse(accepted)
        self.assertIn('missing_or_changed_replacement', rejected[0]['reasons'])
        self.add_learned('learned-001-1')
        updated, accepted, _ = self.apply([operation('DEPRECATE', 'learned-001-0', 'learned-001-1')])
        self.assertEqual(len(accepted), 1)
        self.assertFalse(updated['bullets'][-2]['active'])
        self.assertTrue(updated['bullets'][-1]['active'])

    def test_approved_add_is_scoped_and_empty_delta_keeps_version(self):
        updated, accepted, _ = self.apply([operation()], dataset_scope='Dreaddit')
        self.assertEqual(len(accepted), 1)
        self.assertEqual(updated['version'], 1)
        self.assertEqual(updated['bullets'][-1]['dataset_scope'], ['Dreaddit'])
        self.assertEqual(self.apply([])[0], self.memory)

    def test_guard_technical_failure_holds_instead_of_committing(self):
        class Broken:
            def call(self, *args):
                raise app.CallError('incomplete_output')
        proposal = {'lesson': 'A procedure', 'operations': [operation()]}
        guard = app.guard_delta(Broken(), task(), self.memory, proposal, self.feedback)
        self.assertEqual(guard['status'], 'technical_hold')
        self.assertFalse(self.apply([operation()], guard=guard)[1])

    def test_feedback_failure_preserves_completed_artifact_and_prior_memory(self):
        class Broken:
            def __init__(self, *args):
                self.records = []

            def call(self, *args):
                raise app.CallError('incomplete_output')

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app.write(root/'seed_playbook.json', self.memory)
            packet = {'packet_id': 'p', 'task': task()}
            outcome = {'artifact': artifact(), 'integrity': [], 'audit_history': []}
            with patch.object(app, 'Client', Broken), patch.object(app, 'execute_ta', return_value=outcome), patch.object(app, 'export'):
                memory = app.develop(root, 'dreaddit', 'qwen3:8b', app.BASE_CONFIG, {},
                                     {'dreaddit': {'development': [packet]}}, limit=1)
            record = app.unseal(root/'development/dreaddit/qwen3_8b/001/result.json')
            self.assertEqual(record['status'], 'complete')
            self.assertTrue(record['update_technical_hold'])
            self.assertEqual(record['outcome'], outcome)
            self.assertEqual(memory, self.memory)


if __name__ == '__main__':
    unittest.main()
