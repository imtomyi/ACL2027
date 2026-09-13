"""Software-only optimizer wiring checks; no local model requests or real results."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import dspy
import run as g

class FakeNative:
    def __init__(self,directory):
        self.directory=Path(directory);self.calls=0
        self.last_usage={'prompt_tokens':10,'completion_tokens':8}
    def chat(self,messages,**kw):
        self.calls+=1
        return '[[ ## reasoning ## ]]\nSoftware fixture.\n[[ ## label_ids ## ]]\n[0, 4]\n[[ ## completed ## ]]'

class OptimizerContracts(unittest.TestCase):
    def test_installed_official_constructors_accept_frozen_options(self):
        with tempfile.TemporaryDirectory(dir=g.ROOT/'Storage/experiment_monitor') as temp:
            native=FakeNative(temp);lm=g.LocalLM(native)
            a=dspy.MIPROv2(metric=lambda a,b,trace=None:0.,auto='heavy',prompt_model=lm,
                           task_model=lm,num_threads=1,seed=42,log_dir=temp)
            b=dspy.GEPA(metric=lambda a,b,trace=None,pred_name=None,pred_trace=None:dspy.Prediction(score=0.,feedback='fixture'),
                        auto='heavy',reflection_lm=g.LocalLM(native,temperature=1),num_threads=1,seed=42,log_dir=temp,track_stats=True)
            self.assertEqual(a.auto,'heavy');self.assertEqual(b.auto,'heavy');self.assertEqual(native.calls,0)

    def test_multilabel_provider_serialization_and_cache(self):
        with tempfile.TemporaryDirectory(dir=g.ROOT/'Storage/experiment_monitor') as temp:
            native=FakeNative(temp);lm=g.LocalLM(native)
            with dspy.context(lm=lm,adapter=dspy.ChatAdapter()):
                program=dspy.Predict(g.Emotion.with_instructions(g.TASK))
                first=program(passage='software fixture')
                self.assertEqual(g.parse_labels(first.label_ids),[0,4])
                artifact=Path(temp)/'program.json';program.save(str(artifact))
                restored=dspy.Predict(g.Emotion.with_instructions(g.TASK));restored.load(str(artifact))
                second=restored(passage='software fixture')
                self.assertEqual(g.parse_labels(second.label_ids),[0,4]);self.assertEqual(native.calls,1)

    def check_factory(self,method):
        with tempfile.TemporaryDirectory(dir=g.ROOT/'Storage/experiment_monitor') as temp:
            native=FakeNative(temp);captured={}
            class Recorder:
                def __init__(self,**kw):captured.update(kw)
                def compile(self,program,**kw):captured['data']=kw;return program
            datasets={split:[{'record_id':split,'text':split+' fixture','target':[0,4]}] for split in ['train','dev','test']}
            name='MIPROv2' if method=='miprov2' else 'GEPA'
            with patch.object(g.dspy,name,Recorder):
                g.compile_predictor(method,native,datasets,Path(temp))
            self.assertEqual(captured['auto'],'heavy');self.assertEqual(captured['seed'],42)
            self.assertEqual(captured['num_threads'],1)
            self.assertEqual(set(captured['data']),{'trainset','valset'})
            self.assertEqual(captured['data']['trainset'][0].passage,'train fixture')
            self.assertEqual(captured['data']['valset'][0].passage,'dev fixture')
            metric=captured['metric'];gold=captured['data']['valset'][0]
            correct=metric(gold,dspy.Prediction(label_ids='[4, 0]'))
            invalid=metric(gold,dspy.Prediction(label_ids='invalid'))
            self.assertEqual(correct if method=='miprov2' else correct.score,1.)
            self.assertEqual(invalid if method=='miprov2' else invalid.score,0.)
            with patch.object(g.dspy,name,side_effect=AssertionError('Must reuse compiled artifact')):
                g.compile_predictor(method,native,datasets,Path(temp))
            self.assertEqual(native.calls,0)

    def test_mipro_factory_and_compiled_resume(self):self.check_factory('miprov2')
    def test_gepa_factory_feedback_and_compiled_resume(self):self.check_factory('gepa')

if __name__=='__main__':unittest.main()
