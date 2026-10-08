"""llm.py - the only module that talks to an LLM provider.

Every call is cached on disk under cache/{condition}/{hash}.json, keyed by
(condition, model, max_tokens, system, messages). The cache record holds the full
prompt and the raw response, so it doubles as the prompt/response log.
Swap provider or model here; the harnesses only see call() and its returned dict.
"""
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / "cache"
MODEL = os.environ.get("BR_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 8192  # identical for every condition (raised from 4096: A truncated on 500-node DEV)
# $ per million tokens: (input, output). Cache writes cost 1.25x input, cache reads 0.1x input.
PRICES = {"claude-haiku-4-5-20251001": (1.0, 5.0), "claude-haiku-4-5": (1.0, 5.0)}

_client = None


def cost_usd(model, uncached_in, cache_write, cache_read, out):
    p_in, p_out = PRICES[model]
    return (uncached_in * p_in + cache_write * 1.25 * p_in + cache_read * 0.1 * p_in + out * p_out) / 1e6


def call(condition, system, messages, cache_system=False, model=MODEL, max_tokens=MAX_TOKENS):
    """One chat completion at temperature 0. Returns a dict with text, token counts, latency, cost."""
    global _client
    key = hashlib.sha256(json.dumps([condition, model, max_tokens, system, messages],
                                    sort_keys=True).encode()).hexdigest()[:24]
    path = CACHE / condition / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text()) | {"cached": True}

    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    block = {"type": "text", "text": system}
    if cache_system:
        block["cache_control"] = {"type": "ephemeral"}
    t0 = time.time()
    # anthropic>=1.0 dropped the temperature kwarg; Haiku 4.5 still accepts it in the request body.
    resp = _client.messages.create(model=model, max_tokens=max_tokens, extra_body={"temperature": 0},
                                   system=[block], messages=messages)
    latency = time.time() - t0
    u = resp.usage
    write, read = u.cache_creation_input_tokens or 0, u.cache_read_input_tokens or 0
    rec = dict(condition=condition, model=model, key=key, request_id=resp._request_id,
               stop_reason=resp.stop_reason,
               text="".join(b.text for b in resp.content if b.type == "text"),
               tokens_in=u.input_tokens + write + read, cache_write=write, cache_read=read,
               tokens_out=u.output_tokens, latency_s=round(latency, 3),
               cost_usd=cost_usd(model, u.input_tokens, write, read, u.output_tokens),
               system=system, messages=messages)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1))
    return rec | {"cached": False}


def approx_tokens(text):
    """Offline estimate (~3.3 chars/token for ID-heavy text); used only for dry-run cost estimates."""
    return len(text) / 3.3
