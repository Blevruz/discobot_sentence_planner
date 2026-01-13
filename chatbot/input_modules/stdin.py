# chatbot/input_modules/stdin.py
from input_modules.dummy import DummyInput, input_modules_class
import sys

class StdinInput(DummyInput):

    def action(self, i):
        for line in sys.stdin:
            self.output_queue.put(line)

    def __init__(self, name="stdin_input", **args):
        DummyInput.__init__(self, name)
        self._loop_type = "thread"
        self.datatype_out = "any"

input_modules_class['stdin'] = StdinInput


