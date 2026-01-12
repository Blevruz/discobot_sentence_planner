# chatbot/input_methods/keyboard.py
from input_methods.dummy import DummyInput, input_methods_class
import time

class KeyboardInput(DummyInput):

    def action(self, i):
        while not self.output_queue.empty():
            return
        self.output_queue.put(input("USR> "))
        time.sleep(self.delay)

    def __init__(self, name="keyboard_input", delay=0.01):
        DummyInput.__init__(self, name)
        self.loop_type = "thread"
        self.datatype_out = "string"
        self.delay = delay

input_methods_class['keyboard'] = KeyboardInput
