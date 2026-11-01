"""Thin client for a local Ollama server."""
import json
import re

import requests


class LLM:
    def __init__(self, cfg):
        c = cfg.get("llm", {}) or {}
        self.host = c.get("host", "http://localhost:11434").rstrip("/")
        self.model = c.get("model", "qwen3:1.7b")
        self.timeout = c.get("timeout", 90)

    def _chat(self, system, user, fmt=None):
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "think": False,          # skip Qwen3's slow "thinking" mode
            "keep_alive": -1,        # keep the model loaded in RAM
            "options": {"temperature": 0},
        }
        if fmt is not None:
            body["format"] = fmt
        r = requests.post(f"{self.host}/api/chat", json=body, timeout=self.timeout)
        r.raise_for_status()
        text = r.json()["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

    def chat(self, system, user):
        return self._chat(system, user)

    def chat_json(self, system, user, schema):
        return json.loads(self._chat(system, user, fmt=schema))

    def warmup(self):
        try:
            requests.post(f"{self.host}/api/generate",
                          json={"model": self.model, "keep_alive": -1}, timeout=self.timeout)
            return True
        except requests.RequestException as e:
            print(f"[llm] Ollama not reachable at {self.host}: {e}")
            return False
