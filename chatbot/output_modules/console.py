# chatbot/output_modules/console.py
from output_modules.dummy import DummyOutput, output_modules_class


class ConsoleOutput(DummyOutput):
    """Prints the input to the console, prefixed with a string.
    """

    def action(self, i):
        while not self.input_queue.empty():
            print(f"{self._prefix}{self.input_queue.get()}")
        return

    def __init__(self, name = "console_output", **args):
        """Arguments:
            prefix : str
                Prefix to print before the input
        """
        DummyOutput.__init__(self, name, **args)
        self._prefix = args.get('prefix', "SYS> ")
        self._loop_type = 'thread'
        self.datatype_in = 'string'

output_modules_class['console'] = ConsoleOutput
