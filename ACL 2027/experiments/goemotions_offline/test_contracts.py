"""Software fixtures only. These values never enter experiment outputs."""
import json
from pathlib import Path
import tempfile
import unittest
from run import parse_labels, score, load_jsonl, append, judge_request, Emotion, TASK


class Contracts(unittest.TestCase):
    def test_multilabel_exact_match_and_invalid_denominator(self):
        rows=[dict(prediction=[1,0],target=[0,1]),dict(prediction=[0],target=[0,1]),
              dict(prediction=None,target=[2])]
        metrics=score(rows)
        self.assertEqual(metrics['acc'],1/3)
        self.assertEqual(metrics['invalid'],1)
        self.assertEqual(metrics['micro_f1'],.75)
        self.assertAlmostEqual(metrics['macro_f1'],(1+2/3)/28)

    def test_parse_preserves_multiple_labels_rejects_invalid(self):
        self.assertEqual(parse_labels('[5, 0, 5]'),[0,5])
        for value in ['0','[]','[true]','[28]','[-1]','["1"]','emotion: 1']:
            self.assertIsNone(parse_labels(value))

    def test_interrupted_append_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'predictions.jsonl'
            append(path,dict(record_id='fixture'))
            with path.open('ab') as h: h.write(b'{"record_id":')
            self.assertEqual(load_jsonl(path),[dict(record_id='fixture')])
            self.assertTrue(path.with_suffix('.interrupted_tail').exists())
            append(path,dict(record_id='second'))
            self.assertEqual(len(load_jsonl(path)),2)
            with path.open('ab') as h:h.write(b'not-json\n')
            with self.assertRaises(json.JSONDecodeError):load_jsonl(path)

    def test_judge_payload_has_only_source_and_answer(self):
        messages=judge_request('fixture source','fixture answer')
        self.assertEqual(json.loads(messages[1]['content']),dict(source_passage='fixture source',anonymous_answer='fixture answer'))
        self.assertNotIn('stress-classification',messages[0]['content'])
        self.assertEqual(Emotion.with_instructions(TASK).instructions,TASK)


if __name__=='__main__':unittest.main()
