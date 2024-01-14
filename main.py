"""
Chat Assistant Bot Using LLM

Main Conversation
 -> Weather
   - More weather details?

ToDo:
  - Improve latency between answer and loop to next request. It's not getting the mic ready since the prompt appears
  - Redo Weather tool using new extraction methods
  - Get agent to determine if a "is there anything else" prompt is needed

 """

import logging
import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

import llm
from llm import format_user_msg, format_agent_msg, init_history
from tools.base_tools import Tool, GeneralTool, EndTool
from tools.lighting_tool import LightingTool, LightNotFoundException
from tools.weather_tool import WeatherTool

logger = logging.getLogger(__name__)
_ = load_dotenv()

print("---- Alfred Agent ---")
# Azure config
print("Initializing Azure")
SPEECH_CONFIG = speechsdk.SpeechConfig(
    subscription=os.environ["AZURE_STT_KEY"],
    region=os.environ["AZURE_STT_REGION"]
)
AUDIO_CONFIG = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
# The language of the voice that speaks.
SPEECH_CONFIG.speech_synthesis_voice_name = 'en-CA-LiamNeural'
TTS_SYNTH = speechsdk.SpeechSynthesizer(speech_config=SPEECH_CONFIG,
                                        audio_config=AUDIO_CONFIG)
SPEECH_REC = speechsdk.SpeechRecognizer(speech_config=SPEECH_CONFIG)
print("Initializing Tools...")
try:
    lighting_tool = LightingTool()
    TOOLS = [
        GeneralTool(),
        EndTool(),
        WeatherTool(),
        lighting_tool
    ]
except LightNotFoundException:
    print("WARNING: Will not be able to control lights")
    TOOLS = [
        GeneralTool(),
        EndTool(),
        WeatherTool(),
    ]
    lighting_tool = None


def _print_and_speak(msg):
    print(f"Alfred: {msg}")
    return TTS_SYNTH.speak_text_async(msg).get()


def main():
    """
    Outer conversation, waits for wake word
    """
    model = speechsdk.KeywordRecognitionModel("./wake_model1/final_highfa.table")
    keyword = "Alfred are you there?"
    # Create a local keyword recognizer with the default microphone device for input.
    keyword_recognizer = speechsdk.KeywordRecognizer()
    done = False

    def recognized_cb(evt):
        # Only a keyword phrase is recognized. The result cannot be 'NoMatch'
        # and there is no timeout. The recognizer runs until a keyword phrase
        # is detected or recognition is canceled (by stop_recognition_async()
        # or due to the end of an input file or stream).
        result = evt.result
        if result.reason == speechsdk.ResultReason.RecognizedKeyword:
            logger.debug("RECOGNIZED KEYWORD: {}".format(result.text))
        nonlocal done
        done = True

    def canceled_cb(evt):
        result = evt.result
        if result.reason == speechsdk.ResultReason.Canceled:
            print('CANCELED: {}'.format(result.cancellation_details.reason))
        nonlocal done
        done = True

    # Connect callbacks to the events fired by the keyword recognizer.
    keyword_recognizer.recognized.connect(recognized_cb)
    keyword_recognizer.canceled.connect(canceled_cb)

    # Start keyword recognition.
    while True:
        result_future = keyword_recognizer.recognize_once_async(model)
        print(f"(Say '{keyword}' to trigger)")
        result = result_future.get()

        if result.reason == speechsdk.ResultReason.RecognizedKeyword:
            voice_conversation()


def voice_conversation():
    """
    Handles the voice conversation to the user, calls single_conversation for
    LLM handling
    """
    # ToDo: This should get moved to initialization of the agent
    # ToDo: Replace basic message history with LangChain conversation
    history = init_history()
    # Outer loop for triggering on and off
    _print_and_speak("Yes sir, what can I help you with?")
    while True:
        if lighting_tool is not None:
            lighting_tool.set_listening()
        print(f"You: ", end="")
        request = SPEECH_REC.recognize_once_async().get()
        if lighting_tool is not None:
            lighting_tool.set_done_listening()
        print(f"{request.text}")
        if len(request.text) == 0:
            _print_and_speak("I will take my leave now, call me if you need me.")
            return

        res = single_conversation(request.text, history)

        if res == "<END_CONV>":
            _print_and_speak("Very well sir, I will be here if you need me.")
            return

        # Text to Speech
        _print_and_speak(res)


def single_conversation(request: str, history) -> str:
    """
    Handles a single tool conversation
    """
    # Determine relevant tool
    #   Couldn't do all in one request, LLM was not reliable about its responses
    tool = _determine_tool(request, TOOLS, history)
    logger.debug(f"Tool = {type(tool)}")
    if type(tool) == EndTool:
        return "<END_CONV>"

    # Handle the request
    history.append(format_user_msg(request))
    res = tool.process_request(history)
    history.append(format_agent_msg(res))

    return res


def _determine_tool(req: str, tools: list[Tool], history: list) -> Tool:
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
    for tool in tools:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
