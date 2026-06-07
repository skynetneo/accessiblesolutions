"""
Praxis chat model configuration.

LangChain does not expose Z.AI as a first-class provider prefix, so Praxis
uses a local model alias and maps it to Z.AI's OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

DEFAULT_BASE_MODEL = "zai:glm-5.1"
DEFAULT_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

ZAI_PROVIDER_KEYS = {"zai", "zhipu", "glm"}


def init_praxis_chat_model(model_name: Any):
    """Initialize a chat model, including Praxis' Z.AI alias."""
    if not isinstance(model_name, str):
        return model_name

    if _is_mercury_model(model_name):
        return _make_mercury(model_name)

    if _is_zai_model(model_name):
        return ChatOpenAI(
            model=_zai_model_id(model_name),
            api_key=_zai_api_key(),
            base_url=_zai_base_url(),
        )

    return init_chat_model(model_name)


def model_provider_key(model_name: str) -> str:
    """Return the logical provider key used for cross-provider routing."""
    model_lower = model_name.lower()
    if _is_mercury_model(model_lower):
        return "openai"
    if _is_zai_model(model_lower):
        return "zai"
    return model_lower.split(":", 1)[0].split("/", 1)[0]


def _is_mercury_model(model_name: str) -> bool:
    normalized = model_name.strip().lower()
    provider = normalized.split(":", 1)[0].split("/", 1)[0]
    return provider == "mercury" or normalized.startswith("mercury-")


def _make_mercury(model: str):
    """Inception Labs / Mercury via OpenAI-compatible endpoint."""
    api_key_raw = os.environ.get("MERCURY_API_KEY") or os.environ.get("INCEPTION_API_KEY")
    api_key = SecretStr(api_key_raw) if api_key_raw else None
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=_mercury_base_url(),
        temperature=0.2,
        max_retries=2,
    )


def _is_zai_model(model_name: str) -> bool:
    normalized = model_name.strip().lower()
    provider = normalized.split(":", 1)[0].split("/", 1)[0]
    return provider in ZAI_PROVIDER_KEYS or normalized.startswith("glm-")


def _zai_model_id(model_name: str) -> str:
    normalized = model_name.strip()
    if ":" in normalized:
        return normalized.split(":", 1)[1]
    if "/" in normalized:
        return normalized.split("/", 1)[1]
    return normalized


def _zai_api_key() -> str:
    api_key = os.environ.get("ZAI_API_KEY", "").strip()
    # Keep modules importable in tests that never invoke the model. The first
    # real API call will fail authentication if the environment is incomplete.
    return api_key or "missing-zai-api-key"


def _zai_base_url() -> str:
    return (
        os.environ.get("ZAI_BASE_URL")
        or os.environ.get("ZAI_API_BASE")
        or os.environ.get("ZAI__BASE_URL")
        or DEFAULT_ZAI_BASE_URL
    ).rstrip("/")


def _mercury_base_url() -> str:
    return (
        os.environ.get("MERCURY_BASE_URL")
        or os.environ.get("MERCURY_API_BASE")
        or os.environ.get("MERCURY__BASE_URL")
        or "https://api.inceptionlabs.ai/v1"
    ).rstrip("/")
