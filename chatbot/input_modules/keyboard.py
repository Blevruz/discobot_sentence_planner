# chatbot/input_modules/keyboard.py
from input_modules.dummy import DummyInput, input_modules_class
import time

class KeyboardInput(DummyInput):
    """Keyboard input module. Takes input from the keyboard.
    A delay can be specified between inputs"""

    def action(self, i):
        """Get input from the keyboard using input(),
        then sleep for the specified amount of time"""
        while not self.output_queue.empty():
            return
        self.output_queue.put(input())
        time.sleep(self.delay)

    def __init__(self, name="keyboard_input", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_out = "string"
        self.delay = args.get('delay', 1.0)

input_modules_class['keyboard'] = KeyboardInput
