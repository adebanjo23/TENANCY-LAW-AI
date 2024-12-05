"""Configuration settings for the Lagos Tenancy Law Bot."""

from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


# LLM settings
LLM_CONFIGS = {
    LLMProvider.OPENAI: {
        "model": "gpt-3.5-turbo",
        "temperature": 0.3,
        "max_tokens": 1000
    },
    LLMProvider.GROQ: {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.2,
        "max_tokens": 2000
    },
    LLMProvider.ANTHROPIC: {
        "model": "claude-3-opus-20240229"
    },
    LLMProvider.GEMINI: {
        "model": "gemini-pro"
    }
}

# Default provider
DEFAULT_PROVIDER = LLMProvider.GROQ
