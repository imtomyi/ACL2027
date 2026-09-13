"""Software-only contract tests. Fake responses are never experiment evidence."""
import tempfile
import unittest
from pathlib import Path
import dspy
from comparison import parse_label, scores, data
from optimizers import LocalLM, Stress, dc_adapter


class FakeNative:
    def __init__(self,path):
        self.directory=Path(path)
        self.calls=[]
        self.last_usage=dict(prompt_tokens=10,completion_tokens=5)
    def chat(self,messages,**kwargs):
        self.calls.append((messages,kwargs))
        if kwargs['role']=='curator':
            return '<cheatsheet>software test memory</cheatsheet>'
        if kwargs['role']=='prediction':
            return '<answer>0</answer>'
        return '[[ ## reasoning ## ]]\nSoftware fixture.\n[[ ## label ## ]]\n0\n[[ ## completed ## ]]'


class Contracts(unittest.TestCase):
    def test_parser_and_invalid_denominator(self):
        self.assertIsNone(parse_label('Possibly 0 or 1'))
        self.assertEqual(parse_label('<answer>1</answer>'),'1')
        self.assertEqual(scores([dict(prediction=None,target='1'),dict(prediction='0',target='0')])['accuracy'],.5)

    def test_split_groups(self):
        splits=data()
        groups=[{r['source_id'] for r in splits[k]} for k in ['train','validation','test']]
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])

    def test_official_dc_feedback_noninterference(self):
        with tempfile.TemporaryDirectory() as path:
            no=FakeNative(path); yes=FakeNative(path)
            self.assertEqual(dc_adapter(no)('fixture','(empty)',None)[0],'<answer>0</answer>')
            dc_adapter(yes)('fixture','(empty)','1')
            self.assertEqual(no.calls[0],yes.calls[0])
            self.assertEqual(len(no.calls),2)
            self.assertNotIn('Verified dataset feedback',no.calls[1][0][0]['content'])
            self.assertIn('correct stress label is 1',yes.calls[1][0][0]['content'])
            self.assertEqual(no.calls[1][1]['max_tokens'],4096)

    def test_dspy_provider_and_cache(self):
        with tempfile.TemporaryDirectory() as path:
            native=FakeNative(path); lm=LocalLM(native)
            with dspy.context(lm=lm,adapter=dspy.ChatAdapter()):
                self.assertEqual(dspy.Predict(Stress)(passage='software fixture').label,'0')
                self.assertEqual(dspy.Predict(Stress)(passage='software fixture').label,'0')
            self.assertEqual(len(native.calls),1)
            self.assertEqual(lm.copy(temperature=1).kwargs['temperature'],1)
            self.assertIs(lm.copy().native,native)


if __name__=='__main__':
    unittest.main()
