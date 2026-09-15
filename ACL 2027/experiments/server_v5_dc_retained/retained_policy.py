"""Declared DC variant: reject verified unusable curator output, retain prior memory."""
from pathlib import Path
import hashlib, json, time, urllib.request
from unittest.mock import patch
from core import Native as OriginalNative, digest, load


class CuratorOutputRejected(Exception):
    def __init__(self, evidence):
        super().__init__('Verified unusable curator output')
        self.evidence = evidence


def unusable_completed_response(value):
    return (isinstance(value, dict) and not value.get('error')
            and value.get('done') is False
            and isinstance(value.get('message', {}).get('content'), str)
            and bool(value['message']['content']))


def retained_update(native, memory, next_id, evidence):
    return dict(memory=memory, next_id=next_id, accepted=False,
                candidate_tokens=None, candidate_sha256=None,
                memory_tokens=len(native.tokenizer.encode(memory)),
                decision='rejected_unusable_curator_retained_prior',
                failure_evidence=evidence, policy='dc-verified-output-rejection-v1')


class Native(OriginalNative):
    def structured(self, messages, role, key, schema, validator):
        if role != 'curator' or 'memory_items' not in schema.get('properties', {}):
            return super().structured(messages, role, key, schema, validator)
        proof_path = self.directory.parent / 'inherited_failure.json'
        if proof_path.exists():
            proof = load(proof_path)
            if proof['structured_key'] == key:
                payload = dict(model='qwen3:8b', messages=messages, stream=False, think=False,
                    keep_alive='30m', options=dict(num_ctx=32768, num_predict=8192,
                    temperature=0, seed=self.seed), format=schema)
                assert digest(payload) == proof['request_sha256'], 'Inherited request differs'
                for name, checksum in proof['evidence_files'].items():
                    assert hashlib.sha256((self.directory.parent / name).read_bytes()).hexdigest() == checksum
                outcome = load(self.directory.parent / proof['diagnostic_response'])
                assert unusable_completed_response(outcome)
                raise CuratorOutputRejected(dict(inherited=True, proof_sha256=digest(proof),
                    request_sha256=proof['request_sha256'], new_inference_calls=0,
                    reason='Three exhausted incomplete-response attempts; matching diagnostic confirms partial output.'))
        self.failure_evidence = []
        reason = 'Format retries exhausted'
        for attempt in range(2):
            try:
                raw = self.chat(messages, role, key + f':format:{attempt}', schema)
            except ValueError as exc:
                if str(exc) == 'Incomplete generated JSON':
                    continue
                if str(exc) == 'Length exhaustion; truncated response discarded':
                    reason = str(exc)
                    break
                raise
            try:
                value = json.loads(raw)
                validator(value)
                json.dumps(value, ensure_ascii=False).encode('utf-8')
                return value
            except (ValueError, TypeError, KeyError, AssertionError):
                continue
        # Include cached closed responses when this is a resumed format failure.
        for path in self.directory.glob('*.attempt*.json'):
            record = load(path)
            if record.get('key') in [key + ':format:0', key + ':format:1'] and record.get('status') == 'success':
                self.failure_evidence.append(dict(path=str(path.relative_to(self.directory.parent)),
                    response_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if not self.failure_evidence:
            raise RuntimeError('No closed response evidence for curator rejection')
        raise CuratorOutputRejected(dict(inherited=False, reason=reason, responses=self.failure_evidence))

    def chat(self, messages, role, key, schema=None, temperature=0):
        original_open = urllib.request.urlopen
        captured = []
        native = self
        class Capture:
            def __init__(self, response, request):
                self.response, self.request = response, request
            def __enter__(self):
                self.response.__enter__()
                return self
            def __exit__(self, *args): return self.response.__exit__(*args)
            def read(self, *args):
                raw = self.response.read(*args)
                path = native.directory.parent / 'transport_evidence' / (digest(key) + '.' + str(time.time_ns()) + '.json')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                evidence = dict(path=str(path.relative_to(native.directory.parent)),
                    response_sha256=hashlib.sha256(raw).hexdigest(),
                    request_body_sha256=hashlib.sha256(self.request.data).hexdigest(), key=key)
                value = json.loads(raw)
                captured.append((value, evidence))
                if role == 'curator' and not value.get('error'):
                    native.failure_evidence.append(evidence)
                return raw
        def opening(request, *args, **kwargs):
            return Capture(original_open(request, *args, **kwargs), request)
        try:
            with patch.object(urllib.request, 'urlopen', opening):
                return super().chat(messages, role, key, schema, temperature)
        except RuntimeError as exc:
            if (role == 'curator' and str(exc) == 'Incomplete inference response'
                    and captured and unusable_completed_response(captured[-1][0])):
                raise ValueError('Incomplete generated JSON') from exc
            raise
