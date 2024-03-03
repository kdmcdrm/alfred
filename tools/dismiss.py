from abc import ABC, abstractmethod
from base import Tool


class DismissTool(Tool):
    name = "END"
    desc = """
    For requests to end the conversation, or general statements of dismissal like 'thanks' or 'that will do'."""

    def process_request(self, messages: list[dict]) -> str:
        return "<END>"
