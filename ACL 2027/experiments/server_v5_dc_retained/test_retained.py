"""Internal rejection-policy tests, never experimental evidence."""
from pathlib import Path
import tempfile, unittest
from test_adaptation import NativeFixture, TASK, OUTPUT
from adapters import DC, Upstream
from retained_policy import Native, CuratorOutputRejected, unusable_completed_response
import os


class PolicyTests(unittest.TestCase):
    def test_only_closed_partial_model_output_qualifies(self):
        self.assertTrue(unusable_completed_response(dict(done=False, message={'content': '{'})))
        for value in [{}, {'done': False}, {'error': 'server down', 'done': False, 'message': {'content': '{'}},
                      {'done': True, 'message': {'content': '{}'}}]:
            self.assertFalse(unusable_completed_response(value))

    def test_verified_rejection_retains_memory_without_invented_curator(self):
        class Rejected(NativeFixture):
            def structured(self, messages, role, key, schema, validator):
                if role == 'curator': raise CuratorOutputRejected({'test_receipt': 'internal'})
                return super().structured(messages, role, key, schema, validator)
        n = Rejected(); events = []
        update = DC(n, Upstream(Path(os.environ['ADAPTATION_UPSTREAM'])), TASK).step(
            {'text': 'x'}, 'previous', 9, 'test', OUTPUT,
            lambda v: self.fail('Existing prediction regenerated'), lambda: events.append('reference'))
        self.assertEqual(events, ['reference'])
        self.assertEqual(update['memory'], 'previous'); self.assertEqual(update['next_id'], 9)
        self.assertFalse(update['accepted']); self.assertIsNone(update['candidate_sha256'])
        self.assertNotIn('curator_response', update)

    def test_ordinary_infrastructure_failure_propagates(self):
        class Broken(NativeFixture):
            def structured(self, *args): raise RuntimeError('Server unavailable')
        with self.assertRaisesRegex(RuntimeError, 'Server unavailable'):
            DC(Broken(), Upstream(Path(os.environ['ADAPTATION_UPSTREAM'])), TASK).step(
                {'text': 'x'}, 'previous', 1, 'test', OUTPUT, lambda v: None, lambda: None)

    def test_two_format_attempts_then_rejection_with_evidence(self):
        class Invalid(Native):
            def chat(self, *args, **kwargs):
                self.calls += 1
                self.failure_evidence.append({'internal_fixture': self.calls})
                return 'invalid JSON'
        with tempfile.TemporaryDirectory() as temp:
            n = Invalid.__new__(Invalid); n.directory = Path(temp); n.calls = 0
            with self.assertRaises(CuratorOutputRejected):
                n.structured([], 'curator', 'test', {'properties': {'memory_items': {}}}, lambda v: None)
            self.assertEqual(n.calls, 2)

    def test_success_keeps_all_fields(self):
        class Valid(Native):
            def chat(self, *args, **kwargs): return '{"memory_items": [{"description": "internal test"}]}'
        with tempfile.TemporaryDirectory() as temp:
            n = Valid.__new__(Valid); n.directory = Path(temp)
            self.assertEqual(n.structured([], 'curator', 'test', {'properties': {'memory_items': {}}},
                            lambda v: None), {'memory_items': [{'description': 'internal test'}]})


if __name__ == '__main__': unittest.main()
