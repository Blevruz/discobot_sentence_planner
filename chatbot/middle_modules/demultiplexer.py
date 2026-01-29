# chatbot/middle_modules/demultiplexer.py
from middle_modules.dummy import DummyMiddle, middle_modules_class

class Demultiplexer(DummyMiddle):
    """Demultiplexer module. Takes input from one queue and outputs to many"""

    def action(self, i):
        v = self.input_queue.get()
        if v:
            for oq in self._output_queues['output']:
                oq.put(v)

    def __init__(self, name="demultiplexer", **args):
        """Initializes the module. No parameters"""
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self._output_queues['output']._size = -1

middle_modules_class['demultiplexer'] = Demultiplexer
