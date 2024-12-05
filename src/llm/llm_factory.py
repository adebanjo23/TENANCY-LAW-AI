"""Factory for creating LLM instances."""

from src.config import LLMProvider, LLM_CONFIGS
from src.llm.llm_providers import OpenAILLM, GroqLLM, AnthropicLLM, GeminiLLM


def create_llm(provider: LLMProvider, api_key: str):
    """Create an LLM instance based on the provider."""
    config = LLM_CONFIGS[provider]

    if provider == LLMProvider.OPENAI:
        return OpenAILLM(api_key=api_key, **config)
    elif provider == LLMProvider.GROQ:
        return GroqLLM(api_key=api_key, **config)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicLLM(api_key=api_key, **config)
    elif provider == LLMProvider.GEMINI:
        return GeminiLLM(api_key=api_key, **config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")