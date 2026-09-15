"""Shared, predeclared inference policy for a fresh comparison (never an old-run overlay)."""
from pathlib import Path
import hashlib
import json
import os
import time

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = 'run_20260914_uniform'
POLICY = dict(
    revision='uniform-local-v1', model='qwen3:8b', quantization='Q4_K_M',
    context=32768, seed=42, thinking=False,
    initial_output_caps=dict(prediction=4096, generator=4096, optimization=4096,
                             reflector=4096, curator=8192, quality_judge=384),
    maximum_output_tokens=16384, memory_tokens=4096,
    length_policy='Discard truncated output; double cap only on length, at most 16384 and available context. Same rule for every method from item zero. Judges retain 384; unresolved stays unknown.',
    memory_policy='Reject a complete candidate exceeding 4096 Qwen tokens; retain the previous valid memory and record the event. Never slice memory or source text.',
    curator_instruction='Keep the complete updated adaptation memory within 4096 Qwen tokens. Use concise general rules and preserve the required output format.',
    cache_policy='Fresh run-local caches only; no old predictions, compiled optimizers, demonstrations, judgments or playbooks imported.',
    temperature_policy='Prediction, generator, curator, reflector and judge use 0; official optimizer proposal temperatures are preserved and logged.',
    scope='24 rows, four datasets, same 100 evaluation IDs per dataset. Local transfers with bounded optimizer budgets, not exact paper reproduction.')


def enabled():
    return os.environ.get('EXPERIMENT_RUN_ID') == RUN_ID


def event(native, name, value):
    with (native.directory/name).open('a') as handle:
        handle.write(json.dumps(dict(at=time.time(), revision=POLICY['revision'], **value))+'\n')


def wrap_chat(original):
    def chat(self, messages, max_tokens=4096, temperature=0, role='prediction', output_format=None):
        if role not in POLICY['initial_output_caps']:
            raise RuntimeError('Unspecified role in frozen uniform protocol: '+role)
        messages = [dict(m) for m in messages]
        if role == 'curator':
            messages[-1]['content'] += '\n\n'+POLICY['curator_instruction']
        if role != 'optimization':
            temperature = 0
        count = len(self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            enable_thinking=False, return_dict=False))
        cap = POLICY['initial_output_caps'][role]
        available = POLICY['context']-count
        if available < cap:
            raise RuntimeError('Uniform context reserve exceeded; no input truncation allowed')
        ceiling = cap if role == 'quality_judge' else min(POLICY['maximum_output_tokens'], available)
        digest = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        while True:
            self.last_usage = {}
            started = time.time()
            error = None
            response = None
            try:
                response = original(self, messages, max_tokens=cap, temperature=temperature,
                                    role=role, output_format=output_format)
            except Exception as exc:
                error = exc
            reason = self.last_usage.get('done_reason')
            event(self, 'uniform_calls.jsonl', dict(role=role, input_sha256=digest,
                input_tokens=count, output_cap=cap, temperature=temperature,
                done_reason=reason, seconds=time.time()-started,
                error_type=type(error).__name__ if error else None))
            if reason != 'length':
                if error is not None:
                    raise error
                return response
            if cap == ceiling:
                # Existing judge handling catches ValueError and records unknown after bounded attempts.
                raise ValueError('Output truncated at frozen uniform ceiling; partial output discarded') from error
            cap = min(cap*2, ceiling)
    chat.uniform_revision=POLICY['revision']
    return chat


def bounded_memory(native, previous, candidate):
    count = len(native.tokenizer.encode(candidate))
    if count <= POLICY['memory_tokens']:
        return candidate, True
    assert len(native.tokenizer.encode(previous)) <= POLICY['memory_tokens']
    event(native, 'memory_limit_events.jsonl', dict(candidate_tokens=count,
        retained_previous=True, candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest()))
    return previous, False


def freeze_config(config):
    """A new config from actual current sources; historical configs are never rewritten."""
    import comparison
    assert getattr(comparison.Native.chat,'uniform_revision',None)==POLICY['revision'], 'Use run_uniform.py for a uniform run'
    config['legacy_requested_caps'] = config.get('caps', {})
    config['caps'] = dict(POLICY['initial_output_caps'], playbook=POLICY['memory_tokens'],
                          maximum_output_tokens=POLICY['maximum_output_tokens'])
    config['uniform_policy'] = POLICY
    config['protocol'] = POLICY['revision']
    config['deadline_seconds'] = None
    files = [Path(p) for p in config['code']]
    files += [Path(__file__), Path(__file__).with_name('run_uniform.py')]
    config['code'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return config


def verify_seal():
    manifest = ROOT/'Storage/budget_pilot'/RUN_ID/'protocol.json'
    data = json.loads(manifest.read_text())
    assert data['policy'] == POLICY
    for path, digest in data['code'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Frozen source changed: '+path

