"""Internal software fixtures; not experiment data or manuscript evidence."""
from pathlib import Path
import json, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server_v5'))
from core import Native
from recover_dc import recovery_native, unicode_scalar_strings, preserve_feedback, atomic


class RecoveryTests(unittest.TestCase):
    def test_unicode_acceptance_is_lossless(self):
        value = {'memory_items': ['English 한글 😀 e\u0301 <tag>']}
        before = json.dumps(value)
        unicode_scalar_strings(value)
        self.assertEqual(json.dumps(value), before)
        with self.assertRaises(UnicodeEncodeError):
            unicode_scalar_strings({'memory_items': ['bad\ud800']})

    def test_unicode_uses_existing_format_retry_without_request_change(self):
        class Base:
            structured = Native.structured
            def __init__(self): self.calls = []
            def chat(self, messages, role, key, schema):
                self.calls.append((messages, role, key, schema))
                return json.dumps({'memory_items': ['bad\ud800' if key.endswith(':0') else 'valid']})
        n = recovery_native(Base)()
        schema = {'properties': {'memory_items': {}}}
        self.assertEqual(n.structured([], 'curator', 'k', schema, lambda v: None),
                         {'memory_items': ['valid']})
        self.assertEqual([c[2] for c in n.calls], ['k:format:0', 'k:format:1'])
        self.assertTrue(all(c[3] is schema for c in n.calls))

    def test_unicode_exhaustion_stays_failed(self):
        class Base:
            structured = Native.structured
            def chat(self, *args): return json.dumps({'memory_items': ['bad\ud800']})
        with self.assertRaisesRegex(ValueError, 'Format retries exhausted'):
            recovery_native(Base)().structured([], 'curator', 'k',
                {'properties': {'memory_items': {}}}, lambda v: None)

    def test_incomplete_retries_are_bounded_and_other_errors_are_not_retried(self):
        class Base:
            def __init__(self): self.calls = 0; self.error = 'Incomplete inference response'
            def chat(self, *args, **kwargs):
                self.calls += 1
                raise RuntimeError(self.error)
        n = recovery_native(Base)()
        with patch('recover_dc.time.sleep'), self.assertRaisesRegex(RuntimeError, 'Incomplete'):
            n.chat('same request')
        self.assertEqual(n.calls, 3)
        n.calls = 0; n.error = 'Other failure'
        with self.assertRaisesRegex(RuntimeError, 'Other failure'): n.chat('same request')
        self.assertEqual(n.calls, 1)

    def test_feedback_reveal_receipt_is_preserved_and_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'feedback_receipts/evaluation_019.json'
            value = dict(prediction_sha256='test', committed_at=1, revealed_at=2)
            atomic(path, value); before = path.read_bytes()
            write = preserve_feedback(atomic)
            write(path, dict(value, revealed_at=3))
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(AssertionError):
                write(path, dict(value, prediction_sha256='different'))


if __name__ == '__main__': unittest.main()
