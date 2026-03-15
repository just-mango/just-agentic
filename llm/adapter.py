"""
LLM Adapter — central wrapper for all LLM calls.
Swap provider by setting LLM_PROVIDER env var:

  LLM_PROVIDER=openai      → OpenAI GPT (default)
  LLM_PROVIDER=openrouter  → OpenRouter (multi-model gateway, dev-friendly)
  LLM_PROVIDER=anthropic   → Anthropic Claude
  LLM_PROVIDER=ollama      → Ollama local (Qwen, etc.)
  LLM_PROVIDER=vllm        → vLLM self-hosted OpenAI-compatible
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage


class LLMAdapter(ABC):
    """Base adapter. All providers implement this interface."""

    @abstractmethod
    def chat_model(self) -> BaseChatModel:
        """Return the underlying LangChain ChatModel.
        Used by create_react_agent() in agent nodes.
        """

    def invoke(self, system_prompt: str, user_input: str) -> str:
        """Simple text-in / text-out call. Used by supervisor for routing."""
        model = self.chat_model()
        response = model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ])
        return response.content


class OpenAIAdapter(LLMAdapter):
    """OpenAI ChatGPT via langchain-openai."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0,
        **kwargs: Any,
    ):
        from langchain_openai import ChatOpenAI
        self._model = ChatOpenAI(
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=temperature,
            **kwargs,
        )

    def chat_model(self) -> BaseChatModel:
        return self._model


class OllamaAdapter(LLMAdapter):
    """Ollama local models via langchain-community.
    Install: pip install langchain-community
    Run:     ollama serve && ollama pull qwen2.5-coder
    """

    def __init__(self, model: str | None = None, **kwargs: Any):
        from langchain_community.chat_models import ChatOllama  # type: ignore
        self._model = ChatOllama(
            model=model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder"),
            **kwargs,
        )

    def chat_model(self) -> BaseChatModel:
        return self._model


class VLLMAdapter(LLMAdapter):
    """vLLM OpenAI-compatible endpoint.
    Expects: VLLM_BASE_URL and VLLM_MODEL env vars.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None, **kwargs: Any):
        from langchain_openai import ChatOpenAI
        self._model = ChatOpenAI(
            model=model or os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct"),
            base_url=base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.getenv("VLLM_API_KEY", "EMPTY"),
            **kwargs,
        )

    def chat_model(self) -> BaseChatModel:
        return self._model


class OpenRouterAdapter(LLMAdapter):
    """OpenRouter — multi-model gateway, useful for dev/testing.
    Sign up at https://openrouter.ai and set OPENROUTER_API_KEY.
    Pick any model with OPENROUTER_MODEL, e.g. "anthropic/claude-3.5-sonnet"

    Install: pip install langchain-openai  (same package, different base_url)
    """

    def __init__(self, model: str | None = None, **kwargs: Any):
        from langchain_openai import ChatOpenAI
        self._model = ChatOpenAI(
            model=model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "just-agentic"),
            },
            **kwargs,
        )

    def chat_model(self) -> BaseChatModel:
        return self._model


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude via langchain-anthropic.
    Install: pip install langchain-anthropic
    Set: ANTHROPIC_API_KEY
    """

    def __init__(self, model: str | None = None, **kwargs: Any):
        from langchain_anthropic import ChatAnthropic  # type: ignore
        self._model = ChatAnthropic(
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            **kwargs,
        )

    def chat_model(self) -> BaseChatModel:
        return self._model


def get_adapter() -> LLMAdapter:
    """Factory: reads LLM_PROVIDER env var and returns the right adapter."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    match provider:
        case "ollama":       return OllamaAdapter()
        case "vllm":         return VLLMAdapter()
        case "openrouter":   return OpenRouterAdapter()
        case "anthropic":    return AnthropicAdapter()
        case _:              return OpenAIAdapter()
