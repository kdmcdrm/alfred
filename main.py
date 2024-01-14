import logging
import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

from agents import OpenAIToolAgent
from tools.base import Tool
from tools.lighting import LightingTool, LightNotFoundException
from tools.dismiss import DismissTool

logger = logging.getLogger(__name__)
_ = load_dotenv()

print("---- Alfred Agent ---")
# Azure config
print("Initializing Azure Speech Services")
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
sys_msg = \
    """You are a helpful butler like Alfred from Batman. You will try to assist and will not refer to the 
fact that you are an AI agent. You are cordial, polite, but also concise and somewhat dry in your 
speech."""
# Initialize lighting separately as we'll use for indicating call/response
try:
    LIGHTING_TOOL = LightingTool(os.environ["LIGHTING_IP"])
    ALFRED = OpenAIToolAgent(
        model_name=os.environ["OPENAI_MODEL_NAME"],
        api_key=os.environ["OPENAI_API_KEY"],
        sys_msg=sys_msg,
        tools=[
            DismissTool(),
            LIGHTING_TOOL
        ]
    )
except LightNotFoundException:
    LIGHTING_TOOL = None
    ALFRED = OpenAIToolAgent(
        model_name=os.environ["OPENAI_MODEL_NAME"],
        api_key=os.environ["OPENAI_API_KEY"],
        sys_msg=sys_msg,
        tools=[
            DismissTool(),
        ]
    )


def _print_and_speak(msg):
    print(f"Alfred: {msg}")
    return TTS_SYNTH.speak_text_async(msg).get()


def main():
    """
    Outer conversation, waits for wake word and call voice_conversation when
    it's received.
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
            run_voice_conversation()


def run_voice_conversation():
    """
    Handles the voice conversation to the user, calls single_conversation for
    LLM handling
    """
    # Outer loop for triggering on and off
    _print_and_speak("Yes sir, what can I help you with?")
    while True:
        if LIGHTING_TOOL is not None:
            LIGHTING_TOOL.set_listening()
        print(f"You: ", end="")
        request = SPEECH_REC.recognize_once_async().get()
        if LIGHTING_TOOL is not None:
            LIGHTING_TOOL.set_done_listening()
        print(f"{request.text}")
        if len(request.text) == 0:
            _print_and_speak("I will take my leave now, call me if you need me.")
            return

        res = ALFRED(request.text)

        if res == "<END_CONV>":
            _print_and_speak("Very well sir, I will be here if you need me.")
            return

        # Text to Speech
        _print_and_speak(res)





if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
