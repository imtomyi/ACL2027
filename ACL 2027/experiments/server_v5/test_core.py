"""No-inference validation of label semantics and literal source evidence."""
import unittest
from core import validate_output,evidence_checks,output_schema
class OutputTests(unittest.TestCase):
 def result(self,labels,quote='stress',start=2,end=8):return dict(label_ids=labels,explanation='Source evidence.',bullet_ids=[],evidence=[dict(label_id=labels[0],quote=quote,start=start,end=end)])
 def test_official_neutral_colabels_remain_legal(self):validate_output(self.result([27,4]),list(range(28)))
 def test_wrong_quotes_fail_quality_not_silently_relocated(self):
  v=self.result([1]);validate_output(v,[0,1],True)
  self.assertEqual(evidence_checks(v,'a stress word')['valid_quotes'],1)
  v['evidence'][0]['start']=0
  self.assertEqual(evidence_checks(v,'a stress word')['valid_quotes'],0)
 def test_unicode_offsets(self):self.assertEqual(evidence_checks(self.result([1],'불안',2,4),'나는불안하다')['valid_quotes'],1)
 def test_bool_not_label(self):
  with self.assertRaises(ValueError):validate_output(self.result([True]),[0,1],True)
 def test_duplicates_invalid(self):
  with self.assertRaises(ValueError):validate_output(self.result([1,1]),[0,1])
 def test_empty_evidence_not_perfect(self):
  v=self.result([1]);v['evidence']=[];validate_output(v,[0,1],True)
  self.assertTrue(evidence_checks(v,'text')['missing_required_evidence'])
 def test_single_label(self):
  with self.assertRaises(ValueError):validate_output(self.result([0,1]),[0,1],True)
 def test_codebook(self):
  with self.assertRaises(ValueError):validate_output(self.result(['invented']),['health','other'])
if __name__=='__main__':unittest.main()
