# chatbot/output_modules/console.py
from output_modules.dummy import DummyOutput, output_modules_class


class ConsoleOutput(DummyOutput):

    def action(self, i):
        while not self.input_queue.empty():
            print(f"SYS> {self.input_queue.get()}")
        return

    def __init__(self, name = "console_output", **args):
        DummyOutput.__init__(self, name)
        self._loop_type = 'thread'
        self._datatype_in = 'string'

output_modules_class['console'] = ConsoleOutput
