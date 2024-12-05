"""Different LLM provider implementations."""
import genai
from src.llm.llm_base import BaseLLM
import openai
from langchain_groq import ChatGroq
from anthropic import Anthropic


class OpenAILLM(BaseLLM):
    """OpenAI implementation."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo",
                 temperature: float = 0.3, max_tokens: int = 1000):
        openai.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_response(self, prompt: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal assistant specializing in Canada Ontario Tenancy Law."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI Error: {str(e)}")


class GroqLLM(BaseLLM):
    """Groq implementation."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant",
                 temperature: float = 0.2, max_tokens: int = 2000):
        self.llm = ChatGroq(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2,
        )

    def get_response(self, prompt: str) -> str:
        try:
            messages = [
                {"role": "system", "content": "You are a legal assistant specializing in Ontario Tenancy Law."},
                {"role": "user", "content": prompt}
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            raise Exception(f"Groq Error: {str(e)}")


class AnthropicLLM(BaseLLM):
    """Anthropic Claude implementation."""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def get_response(self, prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic Error: {str(e)}")


class GeminiLLM(BaseLLM):
    """Google Gemini implementation."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def get_response(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini Error: {str(e)}")