"""Internal software controls only: no corpus generation and no manuscript evidence."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from uniform_protocol import POLICY, bounded_memory, wrap_chat


class UniformPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.native = SimpleNamespace(directory=Path(self.tmp.name), last_usage={},
            tokenizer=SimpleNamespace(apply_chat_template=lambda *a, **kw: range(100),
                                      encode=lambda s: list(s)))
        self.messages = [dict(role='user', content='Internal software control')]

    def test_all_prediction_callers_receive_identical_budget(self):
        seen = []
        def call(native, messages, **kw):
            seen.append(kw['max_tokens'])
            native.last_usage = dict(done_reason='stop')
            return 'complete'
        for cap, role in [(512,'prediction'),(1024,'generator'),(2048,'prediction'),(4096,'optimization')]:
            wrap_chat(call)(self.native,self.messages,max_tokens=cap,role=role)
        self.assertEqual(seen,[4096]*4)

    def test_truncated_partial_is_discarded_and_retry_is_bounded(self):
        caps=[]
        def call(native, messages, **kw):
            caps.append(kw['max_tokens'])
            native.last_usage=dict(done_reason='length')
            return 'partial'
        with self.assertRaises(ValueError):wrap_chat(call)(self.native,self.messages,role='generator')
        self.assertEqual(caps,[4096,8192,16384])

    def test_curator_escalation_and_instruction_do_not_mutate_caller(self):
        caps=[]
        def call(native,messages,**kw):
            self.assertIn(POLICY['curator_instruction'],messages[-1]['content'])
            caps.append(kw['max_tokens'])
            native.last_usage=dict(done_reason='length' if len(caps)==1 else 'stop')
            if len(caps)==1:raise RuntimeError('length')
            return 'complete'
        self.assertEqual(wrap_chat(call)(self.native,self.messages,role='curator'),'complete')
        self.assertEqual(caps,[8192,16384])
        self.assertEqual(self.messages[-1]['content'],'Internal software control')

    def test_context_overflow_rejected_before_call_without_trimming(self):
        self.native.tokenizer.apply_chat_template=lambda *a,**k:range(28000)
        def call(*a,**k):self.fail('Should not send over-context input')
        with self.assertRaises(RuntimeError):wrap_chat(call)(self.native,self.messages,role='curator')

    def test_judge_never_escalates_or_accepts_partial_json(self):
        caps=[]
        def call(native,messages,**kw):
            caps.append(kw['max_tokens']);native.last_usage=dict(done_reason='length')
            return '{}'
        with self.assertRaises(ValueError):wrap_chat(call)(self.native,self.messages,role='quality_judge')
        self.assertEqual(caps,[384])

    def test_memory_rejection_preserves_complete_prior_structure(self):
        previous='[section]\n[id] preserved rule'
        self.assertEqual(bounded_memory(self.native,previous,'x'*4097),(previous,False))
        self.assertEqual(bounded_memory(self.native,previous,'y'*4096),('y'*4096,True))
        self.assertTrue((self.native.directory/'memory_limit_events.jsonl').exists())

    def test_network_error_is_not_misclassified_as_truncation(self):
        seen=[]
        def call(native,messages,**kw):seen.append(1);raise ConnectionError('unavailable')
        with self.assertRaises(ConnectionError):wrap_chat(call)(self.native,self.messages,role='generator')
        self.assertEqual(len(seen),1)


if __name__=='__main__':unittest.main()
