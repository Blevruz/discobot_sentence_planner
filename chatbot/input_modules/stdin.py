# chatbot/input_modules/stdin.py
from input_modules.dummy import DummyInput, input_modules_class
import sys

class StdinInput(DummyInput):
    """Input from stdin"""

    def action(self, i):
        """Reads from stdin and puts it in the output queue"""
        for line in sys.stdin:
            self.output_queue.put(line)

    def __init__(self, name="stdin_input", **args):
        """Initializes the module. No parameters"""
        DummyInput.__init__(self, name, **args)
        self._loop_type = "thread"
        self.datatype_out = "any"

input_modules_class['stdin'] = StdinInput


