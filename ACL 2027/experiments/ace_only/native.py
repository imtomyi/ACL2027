"""Native Ollama adapter extracted unchanged from the recorded local implementation."""
from pathlib import Path
import json
import time
import hashlib
import urllib.request

class Native:
    def __init__(self, directory):
        from transformers import AutoTokenizer
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-8B', local_files_only=True)

    def chat(self, messages, max_tokens=4096, temperature=0, role='prediction', output_format=None):
        count = len(self.tokenizer.apply_chat_template(messages, tokenize=True,
                    add_generation_prompt=True, enable_thinking=False, return_dict=False))
        if count + max_tokens > 32768:
            raise RuntimeError(f'Context overflow: {count} input + {max_tokens} reserved output')
        payload = dict(model='qwen3:8b', messages=messages, stream=False, think=False,
                       keep_alive='30m', options=dict(num_ctx=32768, num_predict=max_tokens,
                                                     temperature=temperature, seed=42))
        if output_format is not None:
            payload['format']=output_format
        started = time.time()
        request = urllib.request.Request('http://127.0.0.1:11434/api/chat',
                   data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=1800) as response:
            result = json.load(response)
        if not result.get('done') or result.get('error'):
            raise RuntimeError('Incomplete local response')
        if result.get('prompt_eval_count',0) < count - 32:
            raise RuntimeError('Potential prompt truncation')
        content = result['message']['content']
        log = dict(role=role, seconds=time.time()-started, prompt_tokens=result.get('prompt_eval_count'),
                   completion_tokens=result.get('eval_count'), done_reason=result.get('done_reason'),
                   input_sha256=hashlib.sha256(json.dumps(messages).encode()).hexdigest())
        self.last_usage = log
        with (self.directory / 'calls.jsonl').open('a') as handle:
            handle.write(json.dumps(log)+'\n')
        if result.get('done_reason') == 'length' and role in ('curator','optimization'):
            raise RuntimeError('Truncated memory or optimizer output; stop instead of silently corrupting state')
        return content
