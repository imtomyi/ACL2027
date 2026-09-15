"""Pinned ACE/DC algorithms with explicit classification-task and runtime adapters."""
from pathlib import Path
import ast, contextlib, io, json, logging, re
from core import output_schema, validate_output, question, digest

SECTIONS = ['STRATEGIES & INSIGHTS', 'FORMULAS & CALCULATIONS',
            'CODE SNIPPETS & TEMPLATES', 'COMMON MISTAKES TO AVOID',
            'PROBLEM-SOLVING HEURISTICS', 'CONTEXT CLUES & INDICATORS', 'OTHERS']
EMPTY = '\n\n'.join('## ' + s for s in SECTIONS)
FORMAT = ('\nTask-transfer output contract: return ONLY the common JSON object with '
          'label_ids, explanation, evidence, and bullet_ids. Map the original reasoning '
          'field to a brief explanation, and the original final_answer to label_ids and '
          'evidence. Do not add reasoning or final_answer fields or answer tags. '
          'The codebook and source task above determine the classification task.')
NO_GT = ('No ground-truth label, correctness score, evaluator judgment, or external '
         'environment feedback is available. Inspect only the source and the committed answer.')


def selected_definitions(path, names, namespace):
    """Execute unchanged upstream function ASTs without provider initialization/imports."""
    tree = ast.parse(Path(path).read_text())
    found = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    assert set(n.name for n in found) == set(names)
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future] + found, type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)


class Upstream:
    def __init__(self, root):
        root = Path(root)
        ns = {'json': json, 're': re}
        selected_definitions(root/'ace/utils.py', ['get_section_slug'], ns)
        names = ['parse_playbook_line', 'get_next_global_id', 'format_playbook_line',
                 'update_bullet_counts', 'apply_curator_operations', 'get_playbook_stats',
                 'extract_playbook_bullets']
        selected_definitions(root/'ace/playbook_utils.py', names, ns)
        self.ace = ns
        self.prompts = {}
        for filename in ['generator.py', 'reflector.py', 'curator.py']:
            tree = ast.parse((root/'ace'/filename).read_text())
            for node in tree.body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                    for name in node.targets:
                        if isinstance(name, ast.Name): self.prompts[name.id] = node.value.value
        dc = {'logger': logging.getLogger('pinned_dc')}
        selected_definitions(root/'dc/extractor.py', ['extract_answer', 'extract_cheatsheet'], dc)
        selected_definitions(root/'dc/language_model.py', ['advanced_generate'], dc)
        self.dc_class = type('PinnedDC', (), {'advanced_generate': dc['advanced_generate']})
        self.dc_generator = (root/'dc/generator_prompt.txt').read_text()
        self.dc_curator = (root/'dc/curator_prompt_for_dc_cumulative.txt').read_text()


def json_object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


REFLECTION = json_object({**{k: {'type': 'string'} for k in
    ['reasoning', 'error_identification', 'root_cause_analysis', 'correct_approach', 'key_insight']},
    'bullet_tags': {'type': 'array', 'items': json_object({
        'id': {'type': 'string'}, 'tag': {'type': 'string', 'enum': ['helpful', 'harmful', 'neutral']}})}})
CURATION = json_object({'reasoning': {'type': 'string'}, 'operations': {'type': 'array',
    'items': json_object({'type': {'type': 'string', 'enum': ['ADD']},
                          'section': {'type': 'string'}, 'content': {'type': 'string'}})}})


def validate_reflection(value):
    if not isinstance(value, dict) or set(value) != set(REFLECTION['properties']): raise ValueError('Reflection fields')
    if any(not isinstance(value[k], str) for k in value if k != 'bullet_tags'): raise ValueError('Reflection text')
    if not isinstance(value['bullet_tags'], list): raise ValueError('Reflection tags')
    for tag in value['bullet_tags']:
        if not isinstance(tag, dict) or set(tag) != {'id', 'tag'} or not isinstance(tag['id'], str) or tag['tag'] not in ['helpful', 'harmful', 'neutral']: raise ValueError('Reflection tag')


def validate_curation(value):
    if not isinstance(value, dict) or set(value) != {'reasoning', 'operations'} or not isinstance(value['reasoning'], str) or not isinstance(value['operations'], list): raise ValueError('Curation fields')
    for op in value['operations']:
        if not isinstance(op, dict) or set(op) != {'type', 'section', 'content'} or op['type'] != 'ADD' or not all(isinstance(op[k], str) for k in ['section', 'content']): raise ValueError('Curation operation')


def complete_cheatsheet(raw):
    tags = re.findall(r'</?cheatsheet\s*>', raw, re.I)
    match = re.search(r'<cheatsheet\s*>(.*?)</cheatsheet\s*>', raw, re.I | re.S)
    if len(tags) != 2 or match is None or not match.group(1).strip(): raise ValueError('Incomplete cheatsheet')
    return match.group(1).strip()


def bounded(native, previous, candidate, next_id, candidate_next_id):
    tokens = len(native.tokenizer.encode(candidate))
    accepted = tokens <= 4096
    return {'memory': candidate if accepted else previous,
            'next_id': candidate_next_id if accepted else next_id,
            'accepted': accepted, 'candidate_tokens': tokens,
            'memory_tokens': len(native.tokenizer.encode(candidate if accepted else previous)),
            'decision': 'accepted' if accepted else 'rejected_over_budget',
            'candidate_sha256': digest(candidate)}


class ACE:
    def __init__(self, native, upstream, task):
        self.native, self.upstream, self.task = native, upstream, task

    def generate(self, source, memory, key):
        prompt = self.upstream.prompts['GENERATOR_PROMPT'].format(memory, '(empty)', question(self.task, source), '') + FORMAT
        return self.native.structured([{'role': 'user', 'content': prompt}], 'generator', key,
            output_schema(self.task['labels'], self.task['single_label']),
            lambda v: validate_output(v, self.task['labels'], self.task['single_label']))

    def update(self, source, prediction, memory, next_id, step, total, reference, key):
        up = self.upstream
        q = question(self.task, source)
        answer = json.dumps({'label_ids': prediction['label_ids'], 'evidence': prediction['evidence']}, ensure_ascii=False)
        used = up.ace['extract_playbook_bullets'](memory, prediction['bullet_ids'])
        if reference is None:
            reflect = up.prompts['REFLECTOR_PROMPT_NO_GT'].format(q, prediction['explanation'], answer, NO_GT, used)
            curator = up.prompts['CURATOR_PROMPT_NO_GT']
        else:
            gt = json.dumps({'label_ids': reference}, ensure_ascii=False)
            feedback = json.dumps({'exact_label_set_correct': set(reference) == set(prediction['label_ids'])})
            reflect = up.prompts['REFLECTOR_PROMPT'].format(q, prediction['explanation'], answer, gt, feedback, used)
            curator = up.prompts['CURATOR_PROMPT']
        reflection = self.native.structured([{'role': 'user', 'content': reflect}], 'reflector', key + ':reflect', REFLECTION, validate_reflection)
        with contextlib.redirect_stdout(io.StringIO()):
            counted = up.ace['update_bullet_counts'](memory, reflection['bullet_tags'])
        context = q + ('\nGround truth for the committed item only: ' + gt if reference is not None else '\n' + NO_GT)
        prompt = curator.format(current_step=step, total_samples=total, token_budget=4096,
            playbook_stats=json.dumps(up.ace['get_playbook_stats'](counted)),
            recent_reflection=json.dumps(reflection, ensure_ascii=False), current_playbook=counted, question_context=context)
        curation = self.native.structured([{'role': 'user', 'content': prompt}], 'curator', key + ':curate', CURATION, validate_curation)
        with contextlib.redirect_stdout(io.StringIO()):
            candidate, candidate_next = up.ace['apply_curator_operations'](counted, curation['operations'], next_id)
        result = bounded(self.native, memory, candidate, next_id, candidate_next)
        result.update(reflection=reflection, curation=curation, operations_proposed=len(curation['operations']),
                      operations_applied=len(curation['operations']) if result['accepted'] else 0)
        return result


class DC:
    def __init__(self, native, upstream, task):
        self.native, self.upstream, self.task = native, upstream, task

    def step(self, source, memory, next_id, key, committed_prediction, commit_prediction, reveal_reference):
        adapter = self
        class Bridge(self.upstream.dc_class):
            def __init__(self): self.calls = 0; self.update_record = None
            def generate(self, history, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    value = committed_prediction
                    if value is None:
                        history = [dict(m) for m in history]
                        history[-1]['content'] += FORMAT
                        value = adapter.native.structured(history, 'generator', key + ':generate',
                            output_schema(adapter.task['labels'], adapter.task['single_label']),
                            lambda v: validate_output(v, adapter.task['labels'], adapter.task['single_label']))
                        commit_prediction(value)
                    return json.dumps(value, ensure_ascii=False)
                if self.calls != 2: raise RuntimeError('DC must perform one generator/curator pair')
                reference = reveal_reference()  # The commit callback has completed and fsynced.
                history = [dict(m) for m in history]
                feedback = NO_GT if reference is None else 'Ground truth for the already committed item: ' + json.dumps({'label_ids': reference})
                history[-1]['content'] += '\n\n' + feedback + '\nKeep the complete updated cheatsheet within 4096 tokenizer tokens. Return exactly one complete <cheatsheet>...</cheatsheet> block.'
                for attempt in range(2):
                    raw = adapter.native.chat(history, 'curator', key + f':curate:format:{attempt}')
                    try: candidate = complete_cheatsheet(raw); break
                    except ValueError:
                        if attempt: raise ValueError('Format retries exhausted') from None
                self.update_record = bounded(adapter.native, memory, candidate, next_id, next_id)
                self.update_record['curator_response'] = raw
                return '<cheatsheet>' + self.update_record['memory'] + '</cheatsheet>'
        bridge = Bridge()
        # Invoke the unchanged upstream cumulative algorithm; never its provider initializer.
        result = bridge.advanced_generate('DynamicCheatsheet_Cumulative', question(self.task, source),
            cheatsheet=memory, generator_template=self.upstream.dc_generator,
            cheatsheet_template=self.upstream.dc_curator, temperature=0, max_tokens=4096,
            max_num_rounds=1, allow_code_execution=False)
        assert bridge.calls == 2 and result['final_cheatsheet'] == bridge.update_record['memory']
        return bridge.update_record
