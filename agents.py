import openai
import logging
from tools.base import Tool
from tools.dismiss import DismissTool

logger = logging.getLogger(__name__)


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

    def answer_user_request(self, request: str) -> str:
        """
        Handles a single conversational turn, using the tools and history
        """
        # Determine relevant tool
        #   Couldn't do all in one request, LLM was not reliable about its responses
        tool = self._determine_tool(request)
        logger.debug(f"Tool = {type(tool)}")
        if type(tool) == DismissTool:
            return "<END_CONV>"

        # Handle the request
        self.history.append(self.format_user_message(request))
        res = tool.process_request(self.history)
        self.history.append(self.format_agent_message(res))

        return res

    def _determine_tool(self, req: str, tools: list[Tool], history: list) -> Tool:
        # ToDo: Fix this
        template = """
        Determine if any of the following tools, delimited by ```, 
        would help with the request following USER: below. 
        Respond with just the name of the tool.

        ```
        {tools}
        ```
        USER: {user_req}
        """
        tool_str = ""
        for tool in self.tools:
            tool_str += f"{tool.name}: {tool.desc}\n"
        req_full = template.format(
            tools=tool_str,
            user_req=req
        )
        # ChatGPT would not answer correctly unless it got only the current message and original message
        msgs = llm.send_msg_recent_hist(req_full, history, 5)
        res = llm.call_chatgpt(msgs)
        for tool in tools:
            if tool.name in res:
                return tool
        # Fall back to general tool if none match
        return GeneralTool()
