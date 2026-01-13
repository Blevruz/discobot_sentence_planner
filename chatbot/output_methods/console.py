# chatbot/output_methods/console.py
from output_methods.dummy import DummyOutput, output_methods_class


class ConsoleOutput(DummyOutput):

    def action(self, i):
        while not self.input_queue.empty():
            print(f"SYS> {self.input_queue.get()}")
        return

    def __init__(self, name = "console_output", **args):
        DummyOutput.__init__(self, name)
        self.loop_type = 'thread'
        self.datatype_in = 'string'

output_methods_class['console'] = ConsoleOutput
