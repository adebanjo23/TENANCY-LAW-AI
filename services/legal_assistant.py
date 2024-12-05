"""Main legal assistant module for handling user queries and contract analysis."""

from utils.prompts import generate_prompt, generate_contract_analysis_prompt
from data.law_text import TENANCY_LAW
from src.llm.llm_base import BaseLLM


class LegalAssistant:
    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def get_response(self, user_query: str, chat_history: str = "") -> str:
        prompt = generate_prompt(
            user_query=user_query,
            law_text=TENANCY_LAW,
            chat_history=chat_history
        )

        try:
            return self.llm.get_response(prompt)
        except Exception as e:
            raise Exception(f"Error processing query: {str(e)}")

    def analyze_contract(self, contract_text: str) -> str:
        prompt = generate_contract_analysis_prompt(
            contract_text=contract_text,
            law_text=TENANCY_LAW
        )

        try:
            return self.llm.get_response(prompt)
        except Exception as e:
            raise Exception(f"Error analyzing contract: {str(e)}")
