# chatbot/output_modules/stdout.py
from output_modules.dummy import DummyOutput, output_modules_class
import sys

class StdoutOutput(DummyOutput):
    """Outputs the input to stdout.
    """

    def action(self, i):
        #out_next = self.input_queue.get()
        out_next = self.input_queue.get()
        if out_next is not None:
            if type(out_next) is bytes:
                sys.stdout.buffer.write(out_next)
            elif type(out_next) is str:
                sys.stdout.write(out_next)

    def __init__(self, name="stdout_output", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "any"

output_modules_class['stdout'] = StdoutOutput
