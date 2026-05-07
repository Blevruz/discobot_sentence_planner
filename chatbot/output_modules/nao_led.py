# chatbot/output_modules/nao_led.py
from output_modules.dummy import DummyOutput, output_modules_class
import utils.nao
import utils.config
from utils.queues import QueueWrapper, QueueSlot
import qi

colors = {
    "red": 0xff0000,
    "green": 0x00ff00,
    "blue": 0x0000ff,
    "yellow": 0xffff00,
    "cyan": 0x00ffff,
    "magenta": 0xff00ff,
    "white": 0xffffff,
    "off": 0x000000
}


class NaoLED(DummyOutput):
    """Sets a set of NAO LEDs on, off, or to a specific color.
    Queues:
        toggle: any
            (default)
            Toggles the LEDs on and off
        color: string or int
            Sets the LEDs to a specific color
            string: one of 
                "red", "green", "blue", "yellow", "cyan", "magenta", "white", "off"
            int: 0x00RRGGBB
        value: float (TODO)
            Sets the LEDs to a specific brightness
            float in [0, 1]
    """

    def action(self, i):
        g = self.input_queue.get()
        if g:
            if self.leds_on:
                self.led.off(self.leds)
            else:
                self.led.on(self.leds)

        g = self.input_queues['color'].get()
        if g:
            if type(g) is str:
                if g in colors:
                    self.led.fadeRGB(self.leds, colors[g], 0.1)
                else:
                    utils.config.debug_print(f"[{self.name}] Invalid color {g}")
            elif type(g) is int:
                self.led.fadeRGB(self.leds, g, 0.1)
            else:
                utils.config.debug_print(f"[{self.name}] Invalid color {g}")









    def __init__(self, name = "nao_led", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'any'

        self._input_queues["color"] = QueueSlot(self, "input", datatype='any')
        self._input_queues["toggle"] = QueueSlot(self, "input", datatype='any')
        self._input_queues["default"] = self._input_queues["toggle"]

        self.ip = args.get("ip", "127.0.0.1")
        self.port = args.get("port", 9559)
        self.session = None
        self.led = None
        self.leds = args.get("leds", ["FaceLeds", "BodyLeds"])
        self.leds_on = args.get("leds_on", True)
        
    def module_start(self):
        self.session = utils.nao.connect(self.ip, self.port)
        self.led = self.session.service("ALLeds")
        utils.config.debug_print(f"[self.name] Initialized NAO LED module {self.name} with ip {self.ip} and port {self.port}")

output_modules_class['nao_led'] = NaoLED
