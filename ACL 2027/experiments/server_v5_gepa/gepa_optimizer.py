"""Pinned DSPy GEPA with full-development corpus F1 selection among validated candidates."""
from pathlib import Path
import hashlib, json, time
import dspy
import optimizer
from optimizer import LocalLM, TaskAdapter, corpus_f1, learned_context
from core import atomic

METRIC_CALLS = 3000
PROBE_METRIC_CALLS = 30
REFLECTION_MINIBATCH = 3


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def objective(task):
    return 'macro' if task['dataset'] == 'dreaddit' else 'micro'


class Ledger:
    """Append-only record of every task prediction, keyed by learned context and passage."""
    def __init__(self, path):
        self.path = Path(path); self.values = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    v = json.loads(line); self.values[(v['context_sha256'], v['passage_sha256'])] = v['label_ids']
    def record(self, context, passage, labels):
        k = (sha(context), sha(passage))
        if k in self.values:
            if self.values[k] != labels: raise RuntimeError('Cached task prediction changed')
            return
        self.values[k] = labels
        with self.path.open('a') as f:
            f.write(json.dumps(dict(context_sha256=k[0], passage_sha256=k[1], label_ids=labels))+'\n'); f.flush()
    def get(self, context, passage):
        return self.values.get((sha(context), sha(passage)))


LEDGER = None


class LedgerAdapter(TaskAdapter):
    def __call__(self, lm, lm_kwargs, signature, demos, inputs):
        value = super().__call__(lm, lm_kwargs, signature, demos, inputs)
        LEDGER.record(learned_context(signature, demos), inputs['passage'], list(value[0]['label_ids']))
        return value


class Program(optimizer.Program):
    def forward(self, passage):
        with dspy.context(adapter=LedgerAdapter()):
            return self.classifier(passage=passage)


def names(task, labels):
    return [f'{label}={task["codebook"][str(label)]}' for label in labels]


def feedback_metric(task, directory):
    progress = directory/'optimization.json'
    calls = [0]
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        expected, predicted = set(gold.label_ids), set(getattr(pred, 'label_ids', []) or [])
        if not predicted:
            score = 0.0
            text = ('The output was invalid: no schema-valid label set was produced. '
                    f'Reference labels: {names(task, sorted(expected))}.')
        else:
            score = 2*len(expected & predicted)/(len(expected)+len(predicted))
            text = f'Reference labels: {names(task, sorted(expected))}. Predicted labels: {names(task, sorted(predicted))}.'
            if expected == predicted: text += ' The prediction is correct.'
            else:
                if expected-predicted: text += f' Missed: {names(task, sorted(expected-predicted))}.'
                if predicted-expected: text += f' Unsupported by the reference: {names(task, sorted(predicted-expected))}.'
        calls[0] += 1
        if calls[0] % 10 == 0:
            current = json.loads(progress.read_text()) if progress.exists() else {}
            current.update(status='running', evaluated_items=calls[0], updated_at=time.time())
            atomic(progress, current)
        return dspy.Prediction(score=score, feedback=text)
    return metric


def select(results, development, task, native):
    """Choose the validated candidate with the highest full-development corpus F1."""
    gold = [list(r['target']) for r in development]
    rows = []
    for index, candidate in enumerate(results.candidates):
        context = learned_context(candidate.classifier.signature, candidate.classifier.demos)
        predicted = [LEDGER.get(context, r['text']) for r in development]
        complete = all(p is not None for p in predicted)
        score = None
        if complete:
            score = 0.0 if any(not p for p in predicted) else 100*corpus_f1(gold, predicted, task['labels'], objective(task))
        rows.append(dict(index=index, context_sha256=sha(context), complete_development_predictions=complete,
                         corpus_objective=score, gepa_mean_score=results.val_aggregate_scores[index],
                         learned_context_tokens=len(native.tokenizer.encode(context)),
                         discovery_metric_calls=results.discovery_eval_counts[index]))
    eligible = [r for r in rows if r['corpus_objective'] is not None]
    if not eligible: raise RuntimeError('No candidate has complete development predictions')
    best = max(eligible, key=lambda r: (r['corpus_objective'], r['gepa_mean_score'], -r['index']))
    return best, rows


def compile_program(native, task, train, development, directory, seed, probe=False):
    global LEDGER
    optimizer.RUNTIME = (native, task, directory)
    LEDGER = Ledger(directory/'prediction_ledger.jsonl')
    lm = LocalLM(native)
    dspy.configure(lm=lm, adapter=dspy.ChatAdapter(), max_history_size=200)
    program = Program(task['instruction'])
    artifact = directory/'compiled.json'
    if artifact.exists():
        program.load(str(artifact)); return program
    budget = PROBE_METRIC_CALLS if probe else METRIC_CALLS
    trainset = [dspy.Example(passage=r['text'], label_ids=r['target']).with_inputs('passage') for r in train]
    valset = [dspy.Example(passage=r['text'], label_ids=r['target']).with_inputs('passage') for r in development]
    progress = directory/'optimization.json'
    prior = json.loads(progress.read_text()) if progress.exists() else {}
    atomic(progress, dict(prior, status='running', train_n=len(trainset), development_n=len(valset),
        planned_metric_calls=budget, reflection_minibatch_size=REFLECTION_MINIBATCH,
        evaluated_items=prior.get('evaluated_items', 0), full_development_evaluations=0,
        started_at=prior.get('started_at', time.time()), objective=objective(task)+'_f1'))
    teleprompter = dspy.GEPA(metric=feedback_metric(task, directory), max_metric_calls=budget,
        reflection_minibatch_size=REFLECTION_MINIBATCH, reflection_lm=LocalLM(native, temperature=1.0),
        num_threads=1, log_dir=str(directory/'gepa'), track_stats=True, seed=seed)
    compiled = teleprompter.compile(program, trainset=trainset, valset=valset)
    results = compiled.detailed_results
    best, rows = select(results, development, task, native)
    chosen = results.candidates[best['index']]
    text = learned_context(chosen.classifier.signature, chosen.classifier.demos)
    if len(chosen.classifier.demos) > 8 or len(native.tokenizer.encode(text)) > 4096:
        raise ValueError('Selected program exceeds shared learned-context budget')
    chosen.save(str(artifact))
    atomic(directory/'candidate_selection.json', dict(selected_index=best['index'], gepa_best_index=results.best_idx,
        objective=objective(task)+'_f1', candidates=rows))
    value = json.loads(progress.read_text())
    value.update(status='complete', compiled_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        learned_context_tokens=len(native.tokenizer.encode(text)), demos=len(chosen.classifier.demos),
        candidates=len(results.candidates), selected_index=best['index'], gepa_best_index=results.best_idx,
        selected_corpus_objective=best['corpus_objective'], evaluated_items=results.total_metric_calls,
        full_development_evaluations=results.num_full_val_evals, completed_at=time.time())
    atomic(progress, value)
    return chosen
