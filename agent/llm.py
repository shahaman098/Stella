"""LLM client — OpenAI-compatible (DGX Spark) with Ollama fallback."""
from __future__ import annotations

import json
import os
import urllib.request

# DGX Spark endpoint (OpenAI-compatible)
DGX_URL   = os.environ.get("DGX_URL",   "http://10.18.216.24:30000")
DGX_MODEL = os.environ.get("DGX_MODEL", "nemotron")

# Ollama fallback (local laptop)
OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def _openai_chat(prompt: str, *, base_url: str, model: str, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model":      model,
        "messages":   messages,
        "max_tokens": 4096,   # nemotron is a reasoning model — needs tokens for CoT + answer
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"].strip()


def _ollama_chat(prompt: str, *, model: str, system: str | None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model":    model,
        "messages": messages,
        "stream":   False,
        "options":  {"temperature": 0.2, "num_predict": 600},
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data.get("message", {}).get("content", "").strip()


def chat(prompt: str, *, system: str | None = None) -> str:
    """Try DGX Spark first, fall back to Ollama."""
    try:
        return _openai_chat(prompt, base_url=DGX_URL, model=DGX_MODEL, system=system)
    except Exception:
        pass
    return _ollama_chat(prompt, model=OLLAMA_MODEL, system=system)
