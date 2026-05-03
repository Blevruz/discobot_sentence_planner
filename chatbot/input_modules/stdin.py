# chatbot/input_modules/stdin.py
from input_modules.dummy import DummyInput, input_modules_class
import sys

unit = [
        "chunk",
        "line",
        "byte"
        ]

class StdinInput(DummyInput):
    """Input from stdin"""

    def action(self, i):
        """Reads from stdin and puts it in the output queue"""
        if self.unit == "line":
            for line in sys.stdin:
                self.output_queue.put(line)
        elif self.unit == "chunk":
            while True:
                chunk = sys.stdin.buffer.read(self.chunk_size)
                if not chunk:
                    break
                self.output_queue.put(chunk)
        elif self.unit == "byte":
            while True:
                byte = sys.stdin.buffer.read(1)
                if not byte:
                    break
                self.output_queue.put(byte)

    def __init__(self, name="stdin_input", **args):
        """Initializes the module. No parameters"""
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_out = "any"
        self.unit = args.get("unit", "chunk")
        if self.unit not in unit:
            raise ValueError("unit must be one of {}".format(unit))
        self.chunk_size = args.get("chunk_size", 1024)
        if self.unit == "chunk":
            self.chunk_size = int(self.chunk_size)


input_modules_class['stdin'] = StdinInput


