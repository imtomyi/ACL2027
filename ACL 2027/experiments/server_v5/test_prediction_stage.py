import unittest
from predict_stage import literal_anchors
class AnchorTests(unittest.TestCase):
 def value(self,quote,start,end):return {'evidence':[{'label_id':1,'quote':quote,'start':start,'end':end}]}
 def test_unique_exact_anchor_keeps_bad_offset_distinct(self):
  v=self.value('stress',0,6);r=literal_anchors(v,'a stress word')[0]
  self.assertEqual(r['resolution'],'unique_exact_match');self.assertFalse(r['reported_offset_valid']);self.assertEqual(r['resolved_start'],2);self.assertEqual(v['evidence'][0]['start'],0)
 def test_ambiguous_quote_not_arbitrarily_relocated(self):
  self.assertIsNone(literal_anchors(self.value('a',1,2),'a a')[0]['resolved_start'])
 def test_valid_location_disambiguates_repeated_quote(self):
  self.assertEqual(literal_anchors(self.value('a',2,3),'a a')[0]['resolved_start'],2)
 def test_fuzzy_quote_rejected(self):self.assertFalse(literal_anchors(self.value('stressed',0,8),'stress')[0]['literal_match'])
 def test_empty_quote_not_perfect(self):self.assertFalse(literal_anchors(self.value('',0,0),'source')[0]['literal_match'])
if __name__=='__main__':unittest.main()
