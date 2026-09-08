"""Native Ollama transport implementing the response interface used by ACE."""

import json
import shutil
import urllib.request
from pathlib import Path
from types import SimpleNamespace


class OllamaClient:
    def __init__(self, url, context_window=32768, seed=42):
        self.url = url.rstrip("/")
        self.context_window = context_window
        self.seed = seed
        self.chat = SimpleNamespace(completions=self)

    def create(self, *, model, messages, temperature=0, max_tokens=4096,
               response_format=None, **kwargs):
        # ACE catches ordinary inference exceptions and scores them as errors.
        # Stop the experiment instead when log persistence is at risk.
        if shutil.disk_usage(Path(__file__).resolve().parent).free < 512 * 1024**2:
            raise SystemExit("Experiment stopped: less than 512 MiB free for logs and checkpoints")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.context_window,
                "seed": self.seed,
            },
        }
        if response_format:
            if response_format.get("type") != "json_object":
                raise ValueError("Only json_object structured output is supported")
            payload["format"] = "json"
        request = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            result = json.load(response)
        if shutil.disk_usage(Path(__file__).resolve().parent).free < 512 * 1024**2:
            raise SystemExit("Experiment stopped: disk space exhausted during inference")
        if result.get("error") or not result.get("done"):
            raise RuntimeError(f"Incomplete Ollama response: {result.get('error')}")
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=result["message"]["content"]),
                finish_reason=result.get("done_reason"),
            )],
            usage=SimpleNamespace(
                prompt_tokens=result.get("prompt_eval_count", 0),
                completion_tokens=result.get("eval_count", 0),
            ),
        )
