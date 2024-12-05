"""Base class for LLM providers."""

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstract base class for LLM implementations."""

    @abstractmethod
    def get_response(self, prompt: str) -> str:
        """Get response from the LLM."""
        pass