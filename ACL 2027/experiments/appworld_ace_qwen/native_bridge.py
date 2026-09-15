"""Route ACE-AppWorld language-model calls to the shared local Qwen3-8B runtime.

Only the language model changes. Prompts, agents, playbook logic, AppWorld and its evaluator
run unmodified. An input that does not fit the context follows upstream LiteLLMGenerator
semantics and yields an empty response; inputs are never truncated. A response the runtime
leaves incomplete (done=false) is retried; if it stays incomplete, its partial text is passed on
and recorded as an event. The final adaptation playbook is additionally saved after the task loop,
which upstream only snapshots every 30 tasks.
"""
from pathlib import Path
import hashlib, json, os, socket, time, urllib.error, urllib.request

MODEL = 'qwen3:8b'
CONTEXT = 32768
OUTPUT_RESERVE = 4096
OUTPUT_CEILING = 16384
_tokenizer = None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic(path, text):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w') as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)


def environment():
    return Path(os.environ['ACE_NATIVE_CALLS']), os.environ['ACE_NATIVE_ENDPOINT'], os.environ['ACE_NATIVE_TOKENIZER']


def count(messages):
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(environment()[2], local_files_only=True)
    return len(_tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                              enable_thinking=False, return_dict=False))


def event(kind, **fields):
    calls = environment()[0]; calls.mkdir(parents=True, exist_ok=True)
    with (calls/'events.jsonl').open('a') as f:
        f.write(json.dumps(dict(kind=kind, at=time.time(), **fields))+'\n')


def post(endpoint, payload):
    """Return the runtime response; after three incomplete responses, the last one is returned as is."""
    for attempt in range(3):
        try:
            request = urllib.request.Request(endpoint+'/api/chat', data=json.dumps(payload).encode(),
                                             headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=1800) as response:
                result = json.load(response)
            if result.get('error'): raise RuntimeError('Inference error: '+str(result['error']))
            if result.get('done') or attempt == 2: return result
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError):
            if attempt == 2: raise
        time.sleep([5, 15][attempt])


def request(messages, options):
    """Return (payload, input_tokens) or (None, input_tokens) when the input does not fit."""
    n = count(messages)
    if n+OUTPUT_RESERVE > CONTEXT:
        return None, n
    settings = {'num_ctx': CONTEXT, 'num_predict': min(OUTPUT_CEILING, CONTEXT-n),
                'temperature': options.get('temperature', 0), 'seed': options.get('seed', 100)}
    if options.get('stop'): settings['stop'] = options['stop']
    return dict(model=MODEL, messages=messages, stream=False, think=False, keep_alive='30m', options=settings), n


def generate(self, messages, tools=None, **kwargs):
    calls, endpoint, _ = environment()
    payload, n = request(messages, {**self.generation_kwargs, **kwargs})
    if payload is None:
        # Upstream returns this empty response when a model's context is exhausted.
        event('context_exhausted', input_tokens=n)
        return {'content': '', 'tool_calls': [], 'cost': 0}
    key = digest(payload); path = calls/f'{key}.json'
    if path.exists():
        record = json.loads(path.read_text())
        if record['request_sha256'] != key: raise RuntimeError('Cached request identity mismatch')
        result = record['result']
    else:
        began = time.monotonic(); result = post(endpoint, payload)
        atomic(path, json.dumps(dict(request_sha256=key, input_tokens=n, seconds=time.monotonic()-began,
                                     result=result)))
    if result.get('done_reason') == 'length': event('output_ceiling', input_tokens=n, request_sha256=key)
    content = result['message']['content']
    if not result.get('done'): event('incomplete_response', input_tokens=n, request_sha256=key, chars=len(content))
    self.may_log_call(dict(model=MODEL, messages=messages, options=payload['options']),
                      dict(content=content, done_reason=result.get('done_reason'),
                           prompt_eval_count=result.get('prompt_eval_count'), eval_count=result.get('eval_count')))
    return {'role': 'assistant', 'content': content, 'tool_calls': None, 'cost': 0.0}


def install():
    import freezegun
    # AppWorld's clock patching walks sys.modules; lazy transformers modules must stay untouched.
    freezegun.configure(extend_ignore_list=['transformers', 'huggingface_hub', 'tokenizers', 'native_bridge'])
    from appworld_experiments.code.ace import adaptation_agent, lite_llm_generator
    lite_llm_generator.LiteLLMGenerator.generate = generate
    original = adaptation_agent.StarAgent.solve_tasks
    def solve_tasks(self, *args, **kwargs):
        value = original(self, *args, **kwargs)
        destination = os.environ.get('ACE_FINAL_PLAYBOOK')
        if destination and getattr(self, 'playbook', None) is not None:
            atomic(destination, self.playbook)
        return value
    adaptation_agent.StarAgent.solve_tasks = solve_tasks
