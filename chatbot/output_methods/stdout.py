# chatbot/output_methods/stdout.py
from output_methods.dummy import DummyOutput, output_methods_class
import sys

class StdoutOutput(DummyOutput):

    def action(self, i):
        #out_next = self.input_queue.get()
        while not self.input_queue.empty():
            out_next = self.input_queue.get()
            if type(out_next) is bytes:
                sys.stdout.buffer.write(out_next)
            elif type(out_next) is str:
                sys.stdout.write(out_next)

    def __init__(self, name="stdout_output", **args):
        DummyOutput.__init__(self, name)
        self.loop_type = "thread"
        self.datatype_in = "any"

output_methods_class['stdout'] = StdoutOutput
