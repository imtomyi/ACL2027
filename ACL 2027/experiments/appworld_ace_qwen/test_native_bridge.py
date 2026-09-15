"""Incomplete-response handling in the native bridge: transient recovery, partial pass-through, cache replay."""
import json, os, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import native_bridge as nb

class Resp:
    def __init__(self, body): self.body = json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self, *a): return self.body

class Tests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ.update(ACE_NATIVE_CALLS=self.dir, ACE_NATIVE_ENDPOINT='http://x', ACE_NATIVE_TOKENIZER='t')
        self.agent = types.SimpleNamespace(generation_kwargs={}, may_log_call=lambda *a: None)
    def run_with(self, bodies):
        it = iter(bodies)
        with mock.patch.object(nb, 'count', return_value=100), mock.patch.object(nb.time, 'sleep'), \
             mock.patch.object(nb.urllib.request, 'urlopen', side_effect=lambda *a, **k: Resp(next(it))):
            return nb.generate(self.agent, [{'role': 'user', 'content': 'hi'}])
    def events(self):
        p = Path(self.dir)/'events.jsonl'
        return [json.loads(x)['kind'] for x in p.read_text().splitlines()] if p.exists() else []
    def test_complete(self):
        out = self.run_with([{'done': True, 'message': {'content': 'ok'}}])
        self.assertEqual(out['content'], 'ok'); self.assertEqual(self.events(), [])
    def test_transient_incomplete_recovers(self):
        out = self.run_with([{'done': False, 'message': {'content': 'par'}}, {'done': True, 'message': {'content': 'full'}}])
        self.assertEqual(out['content'], 'full'); self.assertEqual(self.events(), [])
    def test_persistent_incomplete_passes_partial_and_caches(self):
        bad = {'done': False, 'message': {'content': 'partial'}}
        out = self.run_with([bad, bad, bad])
        self.assertEqual(out['content'], 'partial'); self.assertEqual(self.events(), ['incomplete_response'])
        out = self.run_with([])  # replayed from cache, no new request
        self.assertEqual(out['content'], 'partial')
    def test_error_raises(self):
        with self.assertRaises(RuntimeError): self.run_with([{'done': True, 'error': 'boom', 'message': {'content': ''}}])

unittest.main(argv=['x'], verbosity=1)
