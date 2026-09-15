"""Explicitly versioned continuation of failed N=100 runs; never accept truncated output."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'output-cap-recovery-v1'
FLOORS = {'generator': 4096, 'prediction': 4096, 'reflector': 4096, 'curator': 8192}
MAX_OUTPUT = 16384
CONTEXT = 32768


def wrap_chat(original):
    def chat(self, messages, max_tokens=4096, temperature=0, role='prediction', output_format=None):
        # Judges retain the exact original rubric, budget and behavior.
        if role not in FLOORS:
            return original(self, messages, max_tokens=max_tokens, temperature=temperature,
                            role=role, output_format=output_format)
        count = len(self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            enable_thinking=False, return_dict=False))
        available = CONTEXT - count
        if available <= 0:
            raise RuntimeError('Recovery input exceeds context; no input is truncated')
        ceiling = min(MAX_OUTPUT, available)
        cap = min(max(max_tokens, FLOORS[role]), ceiling)
        request_hash = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
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
            truncated = self.last_usage.get('done_reason') == 'length'
            event = dict(revision=REVISION, at=time.time(), role=role,
                         input_sha256=request_hash, input_tokens=count,
                         original_cap=max_tokens, effective_cap=cap,
                         done_reason=self.last_usage.get('done_reason'),
                         seconds=time.time()-started,
                         error_type=type(error).__name__ if error else None)
            with (self.directory/'output_limit_events.jsonl').open('a') as handle:
                handle.write(json.dumps(event)+'\n')
            if not truncated:
                if error is not None:
                    raise error
                return response
            if cap >= ceiling:
                raise RuntimeError('Recovery output still truncated at safe context/output ceiling') from error
            # A larger budget is a different, bounded attempt. No repeated same-cap retry.
            cap = min(cap * 2, ceiling)
    return chat


def main():
    phase, corpus = os.environ['RECOVERY_PHASE'], os.environ['PILOT_CORPUS']
    assert phase in ('online', 'offline')
    manifest = json.loads((ROOT/'Storage/online100/run_20260913/output_cap_recovery.json').read_text())
    assert manifest['revision'] == REVISION
    assert f'{corpus}/{phase}' in manifest['scopes']
    assert manifest['wrapper_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert manifest['floors'] == FLOORS and manifest['max_output'] == MAX_OUTPUT
    # The legacy runners still verify their original source and dataset hashes.
    # The overlay is separately sealed and reported, rather than rewriting those hashes.
    sys.path.insert(0, str(ROOT/'experiments/dreaddit_icl'))
    import comparison
    comparison.Native.chat = wrap_chat(comparison.Native.chat)
    target = ROOT/'experiments'/('online100' if phase == 'online' else 'offline100')/'run.py'
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
