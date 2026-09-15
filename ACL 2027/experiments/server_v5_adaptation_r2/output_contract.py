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


CHEATSHEET_SCHEMA = obj({'cheatsheet': {'type': 'string', 'minLength': 1}})
CURATOR_FORMAT = (
    '\nAPI serialization contract: return ONLY a JSON object with one field '
    'cheatsheet. Its string value must contain the complete updated memory body. '
    'Do not include outer <cheatsheet> or </cheatsheet> tags, code fences, or text '
    'outside the JSON. The adapter supplies those outer tags to the upstream '
    'extractor. Keep the complete memory body within 4096 tokenizer tokens. '
    'Preserve and update the memory according to the original curator instructions.'
)


def validate_cheatsheet(value):
    if not isinstance(value, dict) or set(value) != {'cheatsheet'}:
        raise ValueError('Cheatsheet JSON fields')
    body = value['cheatsheet']
    if not isinstance(body, str) or not body.strip():
        raise ValueError('Empty cheatsheet')
    if '<cheatsheet' in body.lower() or '</cheatsheet' in body.lower():
        raise ValueError('Outer cheatsheet tags belong to the adapter')
