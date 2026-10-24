"""Minimal Ollama /api/chat client (stdlib only).

The agent container can only reach the model through the nginx gateway at
OLLAMA_BASE_URL. It has no other network route.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://llm-gateway:11434")
MODEL = os.environ.get("MODEL", "qwen3:8b")
NUM_CTX = int(os.environ.get("NUM_CTX", "16384"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.3"))
CALL_TIMEOUT_S = float(os.environ.get("CALL_TIMEOUT_S", "180"))
RETRY_WAITS_S = [2, 5, 15]           # backoff between attempts on transient errors
RETRY_STATUS = {502, 503, 504}


class OllamaChat:
    def __init__(self, model: str = MODEL, base_url: str = BASE_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def version(self) -> str:
        """Ollama server version (recorded in every summary: it auto-updated mid-project once)."""
        try:
            with urllib.request.urlopen(self.base_url + "/api/version", timeout=10) as resp:
                return json.loads(resp.read()).get("version", "unknown")
        except (urllib.error.URLError, ConnectionError, ValueError):
            return "unknown"

    def __call__(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,  # Qwen3: skip long hidden reasoning to save time
            "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        }
        if tools:
            payload["tools"] = tools
        body = json.dumps(payload).encode()
        for attempt, wait in enumerate(RETRY_WAITS_S + [None]):
            req = urllib.request.Request(self.base_url + "/api/chat", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=CALL_TIMEOUT_S) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in RETRY_STATUS or wait is None:
                    raise
            except (urllib.error.URLError, ConnectionError):
                if wait is None:
                    raise
            time.sleep(wait)  # transient gateway/host hiccup: back off and retry
        return {
            "message": data.get("message", {}),
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        }
