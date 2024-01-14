import openai
from tools.base import Tool


class OpenAIToolAgent:
    def __init__(self,
                 model_name: str,
                 api_key: str,
                 sys_msg: str,
                 tools: list[Tool]
                 ):
        """
        An OpenAI agent that can call a set of tools for assistance.

        Args:
            model_name: The OpenAI model to use.
            api_key: The OpenAI API key.
            sys_msg: The system message to use
            tools: A list of tools the agent can use to handle requests.
        """
        self.model_name = model_name
        self.client = openai.Client(api_key=api_key)
        self.sys_message = \
            {"role": "system", "content": sys_msg}
        self.history = [self.sys_message]
        self.tools = tools

    @staticmethod
    def format_user_message(content: str) -> dict[str, str]:
        return {"role": "user", "content": content}

    @staticmethod
    def format_agent_message(content: str) -> dict[str, str]:
        return {"role": "assistant", "content": content}

    def __call__(self, request: str) -> str:
        """
        Call the LLM agent with a specific question and context.

        Args:
            request: The user request

        Returns:
            response: The agent's response
        """
        # ToDo: fill this with the tool check followed by sending the request to the tool
        pass
