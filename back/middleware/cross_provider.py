"""
upskill/middleware/cross_provider.py

Cross-provider validation middleware.

Ensures that content generation and validation ALWAYS use different AI
providers to eliminate single-model bias. This is a wrap_model_call
middleware that intercepts model calls and routes to the correct provider
based on whether the current call is generation or validation.

The validator.py handles cross-provider at the content pipeline level.
This middleware handles it at the agent level — so if the coaching or
content team agent itself generates content inline, the validation
still uses a different provider.

Provider rotation:
    zai (glm-5.1)         → validated by google (gemini-3.1-pro)
    zhipu (glm-5)         → validated by google (gemini-3.1-pro)
    openai (gpt-5.2)      → validated by google (gemini-3.1-pro)
    deepseek (v3)          → validated by anthropic (sonnet-4.6)
    anthropic (sonnet-4.6) → validated by google (gemini-3.1-pro)
    google (gemini)        → validated by anthropic (sonnet-4.6)

Usage:
    from middleware.cross_provider import CrossProviderMiddleware

    agent = create_agent(
        model="zai:glm-5.1",
        middleware=[CrossProviderMiddleware(role="content")],
        ...
    )
"""

from __future__ import annotations

import os
from typing import Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from model_factory import DEFAULT_BASE_MODEL, init_praxis_chat_model, model_provider_key


# Static config — cache-friendly (no per-request variables)
GENERATION_MODELS = {
    "content": os.environ.get("PRAXIS_CONTENT_MODEL", os.environ.get("UPSKILL_CONTENT_MODEL", DEFAULT_BASE_MODEL)),
    "assessment": os.environ.get(
        "PRAXIS_ASSESSMENT_GEN_MODEL",
        os.environ.get("UPSKILL_ASSESSMENT_GEN_MODEL", DEFAULT_BASE_MODEL),
    ),
    "coaching": os.environ.get("PRAXIS_COACHING_MODEL", os.environ.get("UPSKILL_COACHING_MODEL", DEFAULT_BASE_MODEL)),
}

VALIDATOR_MAP = {
    "zai":       "google_genai:gemini-3.1-pro-preview",
    "zhipu":     "google_genai:gemini-3.1-pro-preview",
    "glm":       "google_genai:gemini-3.1-pro-preview",
    "openai":    "google_genai:gemini-3.1-pro-preview",
    "deepseek":  "anthropic:claude-sonnet-4-6",
    "anthropic": "google_genai:gemini-3.1-pro-preview",
    "google":    "anthropic:claude-sonnet-4-6",
}

# Detection keywords in messages that indicate a validation call
VALIDATION_SIGNALS = frozenset({
    "validate", "check accuracy", "verify", "rubric",
    "score this", "evaluate quality", "bias check",
})


class CrossProviderMiddleware(AgentMiddleware):
    """Routes model calls to different providers for gen vs validation.

    Detection: scans recent messages for validation signal keywords.
    If found, routes to the validation provider. Otherwise uses the
    generation provider for this role.
    """

    def __init__(self, role: str = "content"):
        super().__init__()
        self.role = role
        gen_model_str = GENERATION_MODELS.get(role, DEFAULT_BASE_MODEL)
        self._gen_model = _init_model(gen_model_str)

        # Determine validation provider from generation provider's prefix
        gen_prefix = model_provider_key(gen_model_str)
        val_model_str = VALIDATOR_MAP.get(gen_prefix, "google_genai:gemini-3.1-pro-preview")
        self._val_model = _init_model(val_model_str)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        is_validation = self._detect_validation(request)
        model = self._val_model if is_validation else self._gen_model
        return handler(request.override(model=model))

    @staticmethod
    def _detect_validation(request: ModelRequest) -> bool:
        """Check if this model call is for validation based on message content."""
        # Check last 3 messages for validation signals
        messages = request.messages[-3:] if len(request.messages) >= 3 else request.messages
        for msg in messages:
            content = ""
            if hasattr(msg, "content") and isinstance(msg.content, str):
                content = msg.content.lower()
            if any(signal in content for signal in VALIDATION_SIGNALS):
                return True
        return False


def _init_model(model_name: str):
    """Initialize a chat model, including Praxis' OpenAI-compatible aliases."""
    return init_praxis_chat_model(model_name)
