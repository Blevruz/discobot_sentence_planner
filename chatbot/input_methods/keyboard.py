# chatbot/input_methods/keyboard.py
from input_methods.dummy import DummyInput, input_methods_class
import time

class KeyboardInput(DummyInput):

    def action(self, i):
        while not self.output_queue.empty():
            return
        self.output_queue.put(input("USR> "))
        time.sleep(self.delay)

    def __init__(self, name="keyboard_input", delay=1.0, timeout=1.0):
        DummyInput.__init__(self, name)
        self.loop_type = "thread"

input_methods_class = dict()
input_methods_class['keyboard'] = KeyboardInput
