"""Software-only fixtures; no experiment scores or manuscript evidence."""
import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('paired',Path(__file__).with_name('run.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
REF={'topic_ids':['education'],'evidence':[{'topic':'education','quote':'School closed.'}],'rationale':'A school closure.'}

class Contracts(unittest.TestCase):
    def test_invalid_reflection_retains_memory_for_both_conditions(self):
        class Fake:
            def __init__(self,response):self.response=response;self.calls=0
            def chat(self,*args,**kwargs):self.calls+=1;return self.response
        value={'reasoning':'fixture','final_answer':'fixture','bullet_ids':[]}
        for raw in ['[]','null','"text"','not-json']:
            for ref in [None,REF]:
                native=Fake(raw)
                self.assertEqual(p.adapt(native,'fixture',value,p.g.EMPTY,1,1,100,ref),
                    (p.g.EMPTY,1,'retained_previous_invalid_reflection'))
                self.assertEqual(native.calls,1)

    def test_nonobject_reference_uses_validation_failure_path(self):
        for value in [[],None,'text']:
            with self.assertRaises(AssertionError):p.validate_reference(value,'cache',{'text':'fixture'})

    def test_reference_traceability_and_label_contract(self):
        self.assertEqual(p.validate_reference(REF,'cache',{'text':'School closed.'}),['education'])
        for values in ([],['bad'],['education','education'],['education','insufficient_context']):
            self.assertIsNone(p.labels(values,'cache'))
        with self.assertRaises(AssertionError):p.validate_reference(REF,'cache',{'text':'Unrelated passage.'})

    def test_reference_only_enters_primary_dc_curator(self):
        native=object.__new__(p.Native);native.reference=REF
        seen=[]
        def capture(self,messages,**kw):seen.append((messages,kw));return '{}'
        original=[{'role':'user','content':'SOURCE'}]
        with patch.object(p.g.CachedNative,'chat',capture):
            for role in ['prediction','generator','quality_judge','curator']:
                native.chat(original,role=role)
            native.chat(original,role='curator',output_format={'properties':{'cheatsheet':{}}})
        self.assertEqual(original[0]['content'],'SOURCE')
        for index in [0,1,2,4]:self.assertEqual(seen[index][0][0]['content'],'SOURCE')
        self.assertIn('Unverified local',seen[3][0][0]['content'])
        self.assertEqual(seen[0][1]['output_format'],p.OUTPUT_SCHEMA)

    def test_official_ace_prompt_paths(self):
        class Fake:
            tokenizer=type('Tokenizer',(),{'encode':lambda self,s:list(s)})()
            def __init__(self):self.calls=[]
            def chat(self,messages,**kw):
                self.calls.append(messages[0]['content'])
                return json.dumps({'bullet_tags':[]} if kw['role']=='reflector' else {'operations':[]})
        value={'reasoning':'Explanation','final_answer':'education','bullet_ids':[]}
        for ref in [None,REF]:
            native=Fake();memory,next_id,status=p.adapt(native,'SOURCE',value,p.g.EMPTY,1,1,100,ref)
            self.assertEqual(status,'accepted');self.assertEqual(next_id,1)
            self.assertEqual(any('Unverified local Qwen3-8B reference annotation' in x for x in native.calls),ref is not None)

    def check_run(self,method):
        with tempfile.TemporaryDirectory(dir=p.RUN.parent) as temp:
            root=Path(temp);(root/'data').mkdir()
            row={'record_id':'fixture','source_id':'test','text':'School closed.'}
            for split in ['adapt','test']:(root/'data'/f'cache_{split}.jsonl').write_text(json.dumps(row)+'\n')
            refs=[];updates=[]
            def reference(c,split,i,r):
                refs.append(split)
                if split=='test':self.assertTrue((root/c/method/'prediction_0000.json').exists())
                return REF
            def adapt(native,q,value,memory,next_id,step,total,ref):
                updates.append(ref);return memory,next_id,'accepted'
            value={'reasoning':'Evidence','bullet_ids':[],'final_answer':'education','selected_topics':['education']}
            with patch.object(p,'RUN',root),patch.object(p.g,'RUN',root),patch.object(p,'Native',lambda d:object()),patch.object(p.g,'generate',return_value=(json.dumps(value),value)),patch.object(p,'adapt',adapt),patch.object(p,'get_reference',reference),patch.object(p,'render',lambda:None):
                p.run_method('cache',method)
            return refs,updates

    def test_offline_has_no_test_feedback(self):
        refs,updates=self.check_run('ace_offline_ref')
        self.assertEqual(refs,['adapt']);self.assertEqual(updates,[REF])

    def test_online_feedback_after_saved_prediction_and_no_gt_is_label_free(self):
        refs,updates=self.check_run('ace_online_ref')
        self.assertEqual(refs,['test']);self.assertEqual(updates,[REF])
        refs,updates=self.check_run('ace_online_no_gt')
        self.assertEqual(refs,[]);self.assertEqual(updates,[None])

if __name__=='__main__':unittest.main()
