"""Pinned DSPy MIPROv2 with full-development corpus F1 selection."""
from pathlib import Path
import hashlib, json, time
from unittest.mock import patch
import dspy
from litellm import ModelResponse
from core import atomic, digest, question
from output_contract import generate as generate_canonical, FORMAT

RUNTIME = None


def corpus_f1(gold, predictions, labels, averaging):
    if len(gold) != len(predictions) or not gold:
        raise ValueError('Full aligned evaluation required')
    counts = {label: [0, 0, 0] for label in labels}
    for expected, predicted in zip(gold, predictions):
        expected, predicted = set(expected), set(predicted)
        if not expected <= set(labels) or not predicted <= set(labels):
            raise ValueError('Unknown label')
        for label in labels:
            if label in expected and label in predicted: counts[label][0] += 1
            elif label in predicted: counts[label][1] += 1
            elif label in expected: counts[label][2] += 1
    f1 = lambda tp, fp, fn: 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0
    if averaging == 'micro': return f1(*(sum(v[i] for v in counts.values()) for i in range(3)))
    if averaging == 'macro': return sum(f1(*v) for v in counts.values())/len(labels)
    raise ValueError('Unsupported corpus objective')


def bootstrap_acceptance(example, prediction, trace=None):
    # Demonstration acceptance is distinct from full-development F1 selection.
    return float(set(example.label_ids) == set(getattr(prediction, 'label_ids', [])))


class LocalLM(dspy.LM):
    def __init__(self, native, **kwargs):
        settings = dict(temperature=0, max_tokens=4096); settings.update(kwargs)
        super().__init__('openai/qwen3:8b', cache=True, **settings)
        self.native = native
    def copy(self, **kwargs):
        settings = dict(self.kwargs, **kwargs); settings.pop('cache', None)
        return LocalLM(self.native, **settings)
    def forward(self, prompt=None, messages=None, **kwargs):
        messages = messages or [dict(role='user', content=prompt)]
        settings = dict(self.kwargs, **kwargs)
        if settings.get('n', 1) != 1: raise ValueError('Single output required')
        cache_key=hashlib.sha256(json.dumps([messages,settings],sort_keys=True,default=str).encode()).hexdigest()
        text = self.native.chat(messages, 'optimization', 'proposal:'+cache_key,
                                temperature=settings.get('temperature', 0))
        prompt_n = self.native.count(messages); output_n = len(self.native.tokenizer.encode(text))
        return ModelResponse(model='qwen3:8b',choices=[dict(index=0,finish_reason='stop',
            message=dict(role='assistant',content=text))],usage=dict(prompt_tokens=prompt_n,
            completion_tokens=output_n,total_tokens=prompt_n+output_n))


def learned_context(signature, demos):
    selected = []
    for demo in demos:
        selected.append(dict(passage=demo.passage,
            output={k:demo[k] for k in ['label_ids','explanation','evidence','bullet_ids'] if k in demo}))
    return signature.instructions + ('\nTraining demonstrations:\n'+json.dumps(selected,ensure_ascii=False) if selected else '')


class TaskAdapter(dspy.Adapter):
    def __call__(self, lm, lm_kwargs, signature, demos, inputs):
        native, task, directory = RUNTIME
        text = learned_context(signature, demos)
        if len(demos)>8 or len(native.tokenizer.encode(text))>4096:
            # Invalid candidate: no shortened demonstrations or model calls.
            return [dict(label_ids=[], explanation='', evidence=[], bullet_ids=[])]
        messages=[dict(role='system',content=text),
                  dict(role='user',content=question(task,dict(text=inputs['passage']))+FORMAT)]
        try:
            value=generate_canonical(native,messages,task,'task:'+digest(messages))
        except ValueError as exc:
            if str(exc)!='Format retries exhausted': raise
            return [dict(label_ids=[], explanation='', evidence=[], bullet_ids=[])]
        return [value]


class Program(dspy.Module):
    def __init__(self, instruction):
        super().__init__()
        signature=dspy.Signature('passage -> label_ids, explanation, evidence, bullet_ids', instruction)
        self.classifier=dspy.Predict(signature)
    def forward(self, passage):
        with dspy.context(adapter=TaskAdapter()):
            return self.classifier(passage=passage)


def evaluator_type(task, directory):
    class AggregateEvaluator(dspy.Evaluate):
        def __call__(self, program, **kwargs):
            result=super().__call__(program, **kwargs)
            expected=[list(example.label_ids) for example,_,_ in result.results]
            predicted=[list(getattr(prediction,'label_ids',[])) for _,prediction,_ in result.results]
            average='macro' if task['dataset']=='dreaddit' else 'micro'
            invalid=sum(not labels for labels in predicted)
            result.score=0.0 if invalid else 100*corpus_f1(expected,predicted,task['labels'],average)
            progress=directory/'optimization.json'
            current=json.loads(progress.read_text()) if progress.exists() else {}
            current.update(status='running',full_development_evaluations=current.get('full_development_evaluations',0)+1,
                evaluated_items=current.get('evaluated_items',0)+len(expected),last_score=result.score,
                objective=average+'_f1',invalid_development_outputs=invalid,updated_at=time.time())
            atomic(progress,current)
            return result
    return AggregateEvaluator


def compile_program(native, task, train, development, directory, seed, probe=False):
    global RUNTIME
    RUNTIME=(native,task,directory)
    lm=LocalLM(native)
    dspy.configure(lm=lm,adapter=dspy.ChatAdapter(),max_history_size=200)
    program=Program(task['instruction'])
    artifact=directory/'compiled.json'
    if artifact.exists():
        program.load(str(artifact));return program
    trainset=[dspy.Example(passage=r['text'],label_ids=r['target']).with_inputs('passage') for r in train]
    valset=[dspy.Example(passage=r['text'],label_ids=r['target']).with_inputs('passage') for r in development]
    atomic(directory/'optimization.json',dict(status='initializing',train_n=len(trainset),development_n=len(valset),
        planned_full_evaluations=3 if probe else 31,proposal_candidates=2 if probe else 10,
        full_development_evaluations=0,evaluated_items=0,started_at=time.time(),
        objective='macro_f1' if task['dataset']=='dreaddit' else 'micro_f1'))
    optimizer=dspy.MIPROv2(metric=bootstrap_acceptance,auto=None,num_candidates=2 if probe else 10,
        prompt_model=lm,task_model=lm,max_bootstrapped_demos=1 if probe else 4,
        max_labeled_demos=1 if probe else 4,num_threads=1,seed=seed,max_errors=1,
        log_dir=str(directory/'optimizer'))
    import dspy.teleprompt.mipro_optimizer_v2 as official
    with patch.object(official,'Evaluate',evaluator_type(task,directory)):
        compiled=optimizer.compile(program,trainset=trainset,valset=valset,num_trials=2 if probe else 30,
            minibatch=False,seed=seed)
    text=learned_context(compiled.classifier.signature,compiled.classifier.demos)
    if len(compiled.classifier.demos)>8 or len(native.tokenizer.encode(text))>4096:
        raise ValueError('Selected program exceeds shared learned-context budget')
    compiled.save(str(artifact))
    value=json.loads((directory/'optimization.json').read_text())
    value.update(status='complete',compiled_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        learned_context_tokens=len(native.tokenizer.encode(text)),demos=len(compiled.classifier.demos),completed_at=time.time())
    atomic(directory/'optimization.json',value)
    return compiled
