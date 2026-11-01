#!/usr/bin/env python3
"""Chat backends for the offline memory experiments: a local Ollama server or any OpenAI-compatible endpoint.

Both return the same small dict, {"text", "prompt_tokens", "gen_tokens", "wall_s"}, so a harness can take either as its
`generate(system, user, seed, opts)` callable. Standard library only. Nothing here reads, stores or prints a credential: for a
paid provider the intended route is a local metering proxy (scripts/arena/provider_proxy.py or a variant of it) that holds the
key and enforces a spend cap, and this module is then pointed at the proxy with a dummy key.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Callable, Dict, Optional

OLLAMA_URL = "http://localhost:11434"
Generate = Callable[[str, str, int, Dict[str, float]], Dict[str, object]]


class SpendCapRefused(RuntimeError):
    """The metering proxy refused the request (HTTP 402): nothing was spent and retrying cannot help."""


def ollama_chat(model: str, system: str, user: str, seed: int, opts: Dict[str, float], num_ctx: int = 4096,
                retries: int = 3, url: Optional[str] = None) -> Dict[str, object]:
    body = json.dumps({"model": model, "stream": False, "keep_alive": "3h",
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "options": dict(opts, seed=seed, num_ctx=num_ctx)}).encode()
    request = urllib.request.Request((url or OLLAMA_URL) + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=900) as handle:
                data = json.load(handle)
            return {"text": data["message"]["content"], "prompt_tokens": data.get("prompt_eval_count"),
                    "gen_tokens": data.get("eval_count"), "wall_s": round(time.time() - started, 2)}
        except (OSError, ValueError, KeyError):
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def openai_chat(base_url: str, model: str, system: str, user: str, seed: int, opts: Dict[str, float],
                api_key: str = "routed-through-the-local-proxy", retries: int = 4, timeout: float = 300) -> Dict[str, object]:
    """POST {base_url}/chat/completions. `opts` uses the Ollama names (temperature, top_p, num_predict)."""
    payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "temperature": opts.get("temperature"), "top_p": opts.get("top_p"), "max_tokens": opts.get("num_predict"),
               "seed": seed, "stream": False}
    body = json.dumps({k: v for k, v in payload.items() if v is not None}).encode()
    request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key})
    for attempt in range(retries):
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as handle:
                data = json.load(handle)
            usage = data.get("usage") or {}
            return {"text": data["choices"][0]["message"].get("content") or "", "prompt_tokens": usage.get("prompt_tokens"),
                    "gen_tokens": usage.get("completion_tokens"), "wall_s": round(time.time() - started, 2)}
        except urllib.error.HTTPError as failure:
            if failure.code == 402:
                raise SpendCapRefused(failure.read()[:300].decode("utf-8", "replace")) from None
            if failure.code in (400, 401, 403, 404, 422) or attempt == retries - 1:
                raise
            time.sleep(4 * (attempt + 1))
        except (OSError, ValueError, KeyError):
            if attempt == retries - 1:
                raise
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("unreachable")


def ollama_generate(model: str, num_ctx: int = 4096) -> Generate:
    return lambda system, user, seed, opts: ollama_chat(model, system, user, seed, opts, num_ctx)


def openai_generate(base_url: str, model: str, api_key: str = "routed-through-the-local-proxy") -> Generate:
    return lambda system, user, seed, opts: openai_chat(base_url, model, system, user, seed, opts, api_key)
