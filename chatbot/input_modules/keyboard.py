# chatbot/input_modules/keyboard.py
from input_modules.dummy import DummyInput, input_modules_class
import time

class KeyboardInput(DummyInput):

    def action(self, i):
        while not self.output_queue.empty():
            return
        self.output_queue.put(input("USR> "))
        time.sleep(self.delay)

    def __init__(self, name="keyboard_input", **args):
        DummyInput.__init__(self, name, **args)
        self._loop_type = "thread"
        self.datatype_out = "string"
        self.delay = args.get('delay', 1.0)

input_modules_class['keyboard'] = KeyboardInput
