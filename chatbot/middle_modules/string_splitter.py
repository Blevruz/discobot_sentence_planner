# chatbot/middle_modules/string_splitter.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueWrapper, QueueSlot
import utils.config

class StringSplitter(DummyMiddle):
    """Splits a string into multiple strings based on a splitter.
    """

    def action(self, i):
        text = self.input_queue.get()
        if text:
            for s in text.split(self.splitter):
                self.output_queue.put(s)

    def __init__(self, name="string_splitter", **args):
        """Arguments:
            splitter : str
                Splitter to use for splitting the string
        """
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.splitter = args.get('splitter', " ")
        self.datatype_in = 'string'
        self.datatype_out = 'string'

middle_modules_class['string_splitter'] = StringSplitter
