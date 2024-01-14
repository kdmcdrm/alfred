from dataclasses import dataclass

from tools.base import Tool
import logging
import os
import json
import subprocess

logger = logging.getLogger(__name__)


class ExtractJsonException(Exception):
    pass


class LightNotFoundException(Exception):
    pass


@dataclass
class LightState:
    """ Tracks the state of an LED. Defaults are the default on state"""
    on_or_off: str = "on"
    cct: bool = True
    brightness: int = 100
    color: tuple[int, int, int] = (0, 0, 0)


def extract_json(astr):
    """
    Gets the contents of a json codeblock
    """
    segs = astr.split("```json")
    if len(segs) == 1:
        return segs[0]
    elif len(segs) == 2:
        return segs[1].split("```")[0]
    else:
        raise ExtractJsonException(f"Found unexpected number of ```json splits in {astr}")


class LightingTool(Tool):

    name = "LIGHTING"
    desc = "For requests that interact with lights"

    def __init__(self, ip="192.168.1.201"):
        """
        Class for controlling a set of LED strip lights
        Args:
            ip: IP address of the light controller.
        """
        self.ip = ip
        # Want to fall back to previous state if needed
        self.prev_state = self._get_led_state()

    @staticmethod
    def _percent_to_int8(perc):
        "Converts to 0 to 255"
        return int(perc * 255 / 100)

    @staticmethod
    def _get_properties(user_req: str) -> dict:
        """
        Determines the lighting properties from the user request
        """
        # ToDo: Replace this with a new sys message in this tool
        msgs = init_history()
        # Note: Getting brightness in 0 to 255 resulted in model asking more questions
        lighting_prompt = """
            The following is a request from a user to change the settings for their lights, please determine
            the the following properties surrounded by ```. 
            ```
            on_or_off: Whether they would like the lights "on" or "off".
            brightness: The light level as an integer from 0 to 100. 0 is off, dim is 25, half is 50,
             and 100 is full brightness.
            color: The light color in RGB format like [255, 0, 0] for red
            default: Set to True if the user requests 'default' or 'usual' settings. Also if they ask for "Warm White"
             or "White" lights.
            ```
            Please respond in the form of JSON object with keys for the properties found. If the user
            does not specify a property then leave it out of the response. 

            The user request follows:
            {user_req}
            """.format(user_req=user_req)
        msgs.append(format_user_msg(lighting_prompt))
        res = call_chatgpt(msgs)
        # Sometimes it's in a code block
        res = extract_json(res)
        logger.debug(f"Get properties: {res}")
        try:
            return json.loads(res)
        except JSONDecodeError:
            return res

    def _get_led_state(self) -> LightState:
        """
        Gets current LED state using the command line tool and parse it to a state
        """
        # Found the cmd line operation worked better than the library calls...
        cmd = f'flux_led --info {self.ip}'
        result = str(subprocess.check_output(cmd, shell=True))
        # Extract required data
        on_or_off = "on" if " ON " in result else "off"
        cct = True if "[CCT:" in result else False
        brightness = 100
        if "Brightness:" in result:
            brightness = int(result.split("Brightness: ")[1][:3].replace("%", "").strip())
        color = (0, 0, 0)
        if "[Color:" in result:
            color = tuple([int(x) for x in result.split("[Color: (")[1].split(")")[0].split(",")])
        return LightState(on_or_off, cct, brightness, color)

    def _set_led_state(self, state: LightState):
        """
        Sets the LED state using the command line tool
        """
        if state.cct:
            cmd = "flux_led {ip} --{on_or_off} -w {brightness}".format(
                ip=self.ip,
                on_or_off=state.on_or_off,
                brightness=state.brightness
            )
            os.system(cmd)
        else:
            cmd = "flux_led {ip} --{on_or_off} -c {color}".format(
                ip=self.ip,
                on_or_off=state.on_or_off,
                color=str(state.color).replace(" ", "").replace("(", "").replace(")", "")
            )
            os.system(cmd)

    def set_listening(self):
        """A setting for when the chat agent is listening"""
        # Not caching here as it's slow, do separately before prompt
        listening_state = LightState(
            on_or_off="on",
            cct=False,
            brightness=0,
            color=(0, 255, 0)
        )
        self._set_led_state(listening_state)

    def set_done_listening(self):
        self._set_led_state(self.prev_state)

    def process_request(self, messages: list[dict]) -> str:
        # Got inconsistent behaviour unless I kept only the last message
        props = self._get_properties(get_message_content(messages[-1]))
        if type(props) == str:
            return props

        return_msg = "I was unsure what to do with the lights."
        state = self.prev_state
        if "on_or_off" in props and props["on_or_off"] == "off":
            state.on_or_off = "off"
            return_msg = "I have turned off the lights as you requested."

        # Turn on with no details, assumes default
        if props == {"on_or_off": "on"} or "default" in props and props["default"]:
            state.on_or_off = "on"
            state.cct = True
            state.brightness = 100
            return_msg = "I have turned on your usual lights."

        if "brightness" in props:
            state.on_or_off = "on"
            state.brightness = props["brightness"]
            new_color = tuple([int(props["brightness"]/100 * x) for x in state.color])
            state.color = new_color
            return_msg = "I have adjusted the lights as you requested"

        if "color" in props:
            state.cct = False
            state.on_or_off = "on"  # on is implied when asking for a color
            r, g, b = props["color"]
            state.color = (r, g, b)
            return_msg = "I have adjusted the lights as you requested"

        self.prev_state = state    # no need to cache here, it's just used for the listening call
        self._set_led_state(state)
        return return_msg + ". Is there anything else I can assist with?"
