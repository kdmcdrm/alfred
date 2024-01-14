from abc import ABC, abstractmethod


class Tool(ABC):
    name = ""
    desc = ""

    @abstractmethod
    def process_request(self, messages: list[dict]) -> str:
        """
        Handles a user request using this tool
        """
        pass
