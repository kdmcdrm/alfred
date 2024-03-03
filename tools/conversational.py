from .base import Tool
class ConversationalTool(Tool):
    name = ""
    desc = ""

    @abstractmethod
    def process_request(self, messages: list[dict]) -> str:
        """
        Handles a user request using this tool
        """
        pass
