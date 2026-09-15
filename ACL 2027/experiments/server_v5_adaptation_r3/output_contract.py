"""Lossless wire-to-canonical encoding: model-selected labels own their evidence."""
from core import validate_output

FORMAT = (
    '\nThe API output format below supersedes only the example JSON/XML output '
    'format in the preceding template. Return one JSON object with decision, '
    'explanation, and bullet_ids. explanation is a brief source-grounded justification. '
    'For classification, decision contains supported_labels: a list of objects with '
    'label_id and evidence. Each selected label owns its evidence list; each evidence '
    'object has quote, start, end. Do not put label_id inside evidence objects. '
    'Choose labels yourself from the task codebook. If the codebook permits '
    'insufficient_context and that is your decision, use decision containing only '
    'insufficient_context: {evidence: [...]}, with no supported_labels. '
    'These are mutually exclusive representations of the same task decision. '
    'Do not include final_answer, reasoning, answer tags, or any other fields. '
    'Do not invent evidence: empty evidence remains permitted when no quote is supplied.'
)


def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def schema(task):
    labels = task['labels']
    label_type = 'integer' if isinstance(labels[0], int) else 'string'
    quote = obj({'quote': {'type': 'string'}, 'start': {'type': 'integer', 'minimum': 0},
                 'end': {'type': 'integer', 'minimum': 0}})
    evidence = {'type': 'array', 'items': quote}
    coding_labels = [x for x in labels if x != 'insufficient_context']
    group = obj({'label_id': {'type': label_type, 'enum': coding_labels}, 'evidence': evidence})
    coded = obj({'supported_labels': {'type': 'array', 'minItems': 1,
        'maxItems': 1 if task['single_label'] else len(coding_labels), 'items': group}})
    decision = coded
    if 'insufficient_context' in labels:
        decision = {'oneOf': [coded, obj({'insufficient_context': obj({'evidence': evidence})})]}
    return obj({'decision': decision, 'explanation': {'type': 'string'},
                'bullet_ids': {'type': 'array', 'items': {'type': 'string'}}})


def canonical(wire, task):
    """Retain every selected label and quote; no guessed label or evidence correction."""
    if not isinstance(wire, dict) or set(wire) != {'decision', 'explanation', 'bullet_ids'}:
        raise ValueError('Wire fields')
    choice = wire['decision']
    if not isinstance(choice, dict): raise ValueError('Wire decision')
    if set(choice) == {'supported_labels'}:
        groups = choice['supported_labels']
        if not isinstance(groups, list) or not groups or len(groups) > (1 if task['single_label'] else len([x for x in task['labels'] if x != 'insufficient_context'])):
            raise ValueError('Wire supported labels')
    elif set(choice) == {'insufficient_context'} and 'insufficient_context' in task['labels']:
        abstention = choice['insufficient_context']
        if not isinstance(abstention, dict) or set(abstention) != {'evidence'}:
            raise ValueError('Wire abstention')
        groups = [{'label_id': 'insufficient_context', 'evidence': abstention['evidence']}]
    else:
        raise ValueError('Wire decision branches')
    labels, evidence = [], []
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'label_id', 'evidence'}:
            raise ValueError('Wire label group')
        label = group['label_id']
        if type(label) != type(task['labels'][0]) or label not in task['labels']:
            raise ValueError('Wire unknown label')
        if 'supported_labels' in choice and label == 'insufficient_context':
            raise ValueError('Abstention is not a coding label')
        if label not in labels: labels.append(label)
        quotes = group['evidence']
        if not isinstance(quotes, list): raise ValueError('Wire evidence list')
        for quote in quotes:
            if not isinstance(quote, dict) or set(quote) != {'quote', 'start', 'end'}:
                raise ValueError('Wire quote fields')
            evidence.append(dict(quote, label_id=label))
    result = dict(label_ids=labels, evidence=evidence, explanation=wire['explanation'], bullet_ids=wire['bullet_ids'])
    validate_output(result, task['labels'], task['single_label'])
    return result


def generate(native, messages, task, key):
    wire = native.structured(messages, 'generator', key, schema(task), lambda value: canonical(value, task))
    return canonical(wire, task)


# A finite serialization format for the original description/example/count items.
# This is an explicit DC task-transfer constraint, not a changed model token cap.
CHEATSHEET_SCHEMA = obj({'memory_items': {'type': 'array', 'minItems': 1, 'maxItems': 24,
    'items': obj({'description': {'type': 'string', 'minLength': 1, 'maxLength': 160},
                  'example': {'type': 'string', 'maxLength': 320},
                  'usage_count': {'type': 'integer', 'minimum': 0, 'maximum': 1000000}})}})
CURATOR_FORMAT = (
    '\nAPI serialization contract: return ONLY a JSON object with memory_items, '
    'an array of 1 to 24 complete items. Each item has description (1 to 160 Unicode '
    'characters), example (0 to 320 characters), and usage_count (integer 0 to 1000000). '
    'Write concise, complete descriptions and examples that fit those bounds. '
    'Select and synthesize the most useful prior and new items according to the '
    'original curator instructions; each selected item should add distinct information. '
    'The adapter renders these complete model-written fields into the original '
    'description/example/count memory-item format. Do not write XML tags, outer '
    'cheatsheet tags, or extra fields. These serialization constraints supersede '
    'the preceding output-template and word-count examples only. The final rendered '
    'memory budget remains 4096 tokenizer tokens. Do not claim that a GT-free '
    'prediction has been verified by a human or an unavailable reference label.'
)


def validate_cheatsheet(value):
    if not isinstance(value, dict) or set(value) != {'memory_items'}:
        raise ValueError('Cheatsheet JSON fields')
    items = value['memory_items']
    if not isinstance(items, list) or not 1 <= len(items) <= 24:
        raise ValueError('Cheatsheet item count')
    for item in items:
        if not isinstance(item, dict) or set(item) != {'description', 'example', 'usage_count'}:
            raise ValueError('Cheatsheet item fields')
        for key, lower, upper in [('description', 1, 160), ('example', 0, 320)]:
            if not isinstance(item[key], str) or not lower <= len(item[key]) <= upper:
                raise ValueError('Cheatsheet text bounds')
        if not item['description'].strip(): raise ValueError('Empty memory description')
        if type(item['usage_count']) != int or not 0 <= item['usage_count'] <= 1000000:
            raise ValueError('Cheatsheet usage count')


def render_cheatsheet(value):
    """Render every model-authored field without truncation, deduplication or fallback."""
    from html import escape
    validate_cheatsheet(value)
    return '\n\n'.join('<memory_item>\n<description>\n' + escape(item['description']) +
        '\n</description>\n<example>\n' + escape(item['example']) +
        '\n</example>\n</memory_item>\n** Count: ' + str(item['usage_count'])
        for item in value['memory_items'])
