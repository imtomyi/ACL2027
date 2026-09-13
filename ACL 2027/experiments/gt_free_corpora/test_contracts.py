"""Software-only contract checks; fixtures are not experimental evidence."""
import json
import unittest
import run

class Contracts(unittest.TestCase):
    def test_question_has_no_label_metadata(self):
        row=dict(text='Software fixture.',record_id='fixture',source_id='fixture',
                 target='SECRET_REFERENCE',judgment='SECRET_JUDGE')
        prompt=run.question('cache',row)
        self.assertNotIn('SECRET_REFERENCE',prompt)
        self.assertNotIn('SECRET_JUDGE',prompt)

    def test_official_no_gt_reflection_and_add_update(self):
        class Fake:
            class Tokenizer:
                def encode(self,text):return text.split()
            tokenizer=Tokenizer()
            def __init__(self):self.calls=[]
            def chat(self,messages,**kw):
                self.calls.append((messages,kw))
                if kw['role']=='reflector':return json.dumps(dict(bullet_tags=[]))
                return json.dumps(dict(operations=[dict(type='ADD',section='others',content='Check the supplied evidence.')]))
        f=Fake();memory,next_id,status=run.adapt(f,'Software fixture.',
            dict(reasoning='Fixture rationale.',final_answer='other',bullet_ids=[]),run.EMPTY,1,1,100)
        self.assertEqual(status,'accepted');self.assertEqual(next_id,2)
        self.assertIn('Check the supplied evidence.',memory)
        self.assertIn('No ground truth or correctness feedback',f.calls[0][0][0]['content'])
        self.assertEqual([x[1]['role'] for x in f.calls],['reflector','curator'])

if __name__=='__main__':unittest.main()
