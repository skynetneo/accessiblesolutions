"""Model factory — Groq primary, Mercury (Inception Labs) fallback, Gemini last.

Designed for two cost/latency tiers:
  - ROUTING: small/cheap, used by the supervisor and tool-routing.
  - REPLY: better quality for user-facing answers but still on the free tier.

Selection is driven by env vars; we intentionally avoid an explicit config file
so deployments only need to set the relevant API keys.
"""
from __future__ import annotations

import os
import importlib
import importlib.util
from typing import Literal
from pydantic import SecretStr

Tier = Literal["routing", "reply"]


def _has_groq() -> bool:
    return bool(os.environ.get("GROQ_API_KEY")) and importlib.util.find_spec("langchain_groq") is not None


def _has_mercury() -> bool:
    return (
        bool(os.environ.get("MERCURY_API_KEY") or os.environ.get("INCEPTION_API_KEY"))
        and importlib.util.find_spec("langchain_openai") is not None
    )


def _has_google() -> bool:
    return bool(os.environ.get("GOOGLE_API_KEY")) and importlib.util.find_spec("langchain_google_genai") is not None


def _make_groq(model: str):
    chat_groq_module = importlib.import_module("langchain_groq")
    chat_groq = getattr(chat_groq_module, "ChatGroq")
    return chat_groq(model=model, temperature=0.2, max_retries=2)


def _make_mercury(model: str):
    """Inception Labs / Mercury via OpenAI-compatible endpoint."""
    from langchain_openai import ChatOpenAI

    api_key_raw = os.environ.get("MERCURY_API_KEY") or os.environ.get("INCEPTION_API_KEY")
    api_key = SecretStr(api_key_raw) if api_key_raw else None
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=os.environ.get("MERCURY_BASE_URL", "https://api.inceptionlabs.ai/v1"),
        temperature=0.2,
        max_retries=2,
    )


def _make_gemini(model: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model)


def get_model(tier: Tier = "reply"):
    """Return a chat model for the given tier.

    Tier mapping:
      - routing: prefer the smallest/fastest free model (8B-class).
      - 
      - reply:   step up to a 70B-class free model when available.
    """
    if _has_groq():
        if tier == "routing":
            return _make_groq(os.environ.get("GROQ_ROUTING_MODEL", "llama-3.1-8b-instant"))
        return _make_groq(os.environ.get("GROQ_REPLY_MODEL", "qwen/qwen3-32b"))

    if _has_mercury():
        return _make_mercury(os.environ.get("MERCURY_MODEL", "mercury-2"))

    if _has_google():
        if tier == "routing":
            return _make_gemini(os.environ.get("GEMINI_ROUTING_MODEL", "gemini-flash-lite-latest"))
        return _make_gemini(os.environ.get("GEMINI_REPLY_MODEL", "gemini-pro-latest"))

    raise RuntimeError(
        "No model provider configured. Set GROQ_API_KEY, MERCURY_API_KEY, or GOOGLE_API_KEY."
    )


# Convenience handles used across the graph.
ROUTING_MODEL = get_model("routing")
REPLY_MODEL = get_model("reply")
