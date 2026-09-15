"""Offline checks for truncation recovery; no model calls or dataset text."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from recover_output_limits import wrap_chat


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.native = SimpleNamespace(directory=Path(self.tmp.name), last_usage={},
            tokenizer=SimpleNamespace(apply_chat_template=lambda *a, **kw: range(100)))

    def test_curator_retries_only_with_larger_budget(self):
        seen = []
        messages = [{'role': 'user', 'content': 'diagnostic input'}]
        def call(native, request, **kw):
            self.assertEqual(request, messages)
            seen.append(kw['max_tokens'])
            native.last_usage = {'done_reason': 'length' if len(seen) == 1 else 'stop'}
            if len(seen) == 1:
                raise RuntimeError('truncated curator')
            return 'complete memory'
        result = wrap_chat(call)(self.native, messages, max_tokens=4096, role='curator')
        self.assertEqual(seen, [8192, 16384])
        self.assertEqual(result, 'complete memory')
        events = [json.loads(x) for x in (self.native.directory/'output_limit_events.jsonl').read_text().splitlines()]
        self.assertEqual([x['effective_cap'] for x in events], seen)

    def test_generator_truncation_return_is_not_accepted(self):
        seen = []
        def call(native, request, **kw):
            seen.append(kw['max_tokens'])
            native.last_usage = {'done_reason': 'length'}
            return 'partial'
        with self.assertRaisesRegex(RuntimeError, 'still truncated'):
            wrap_chat(call)(self.native, [], max_tokens=1024, role='generator')
        self.assertEqual(seen, [4096, 8192, 16384])

    def test_context_ceiling_preserves_input(self):
        self.native.tokenizer.apply_chat_template = lambda *a, **kw: range(28000)
        seen = []
        def call(native, request, **kw):
            seen.append(kw['max_tokens'])
            native.last_usage = {'done_reason': 'stop'}
            return 'complete'
        wrap_chat(call)(self.native, [], role='curator')
        self.assertEqual(seen, [4768])

    def test_network_failure_is_not_retried(self):
        seen = []
        def call(native, request, **kw):
            seen.append(kw['max_tokens'])
            raise ConnectionError('offline')
        with self.assertRaises(ConnectionError):
            wrap_chat(call)(self.native, [], role='curator')
        self.assertEqual(seen, [8192])

    def test_judge_parameters_unchanged(self):
        seen = []
        def call(native, request, **kw):
            seen.append(kw)
            return 'judge result'
        wrap_chat(call)(self.native, [], role='quality_judge', max_tokens=384,
                        temperature=0, output_format={'type': 'object'})
        self.assertEqual(seen[0], dict(role='quality_judge', max_tokens=384,
                                      temperature=0, output_format={'type': 'object'}))
        self.assertFalse((self.native.directory/'output_limit_events.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
