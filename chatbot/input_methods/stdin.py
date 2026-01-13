# chatbot/input_methods/stdin.py
from input_methods.dummy import DummyInput, input_methods_class
import sys

class StdinInput(DummyInput):

    def action(self, i):
        for line in sys.stdin:
            self.output_queue.put(line)

    def __init__(self, name="stdin_input", **args):
        DummyInput.__init__(self, name)
        self.loop_type = "thread"
        self.datatype_out = "any"

input_methods_class['stdin'] = StdinInput


