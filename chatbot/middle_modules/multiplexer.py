# chatbot/middle_modules/multiplexer.py
from middle_modules.dummy import DummyMiddle, middle_modules_class

class Multiplexer(DummyMiddle):
    """Multiplexes multiple input queues into a single output queue.
    """

    def action(self, i):
        #self.output_queue.put(self.input_queue.get())
        # check if any of the input queues are not empty
        for queue in self._input_queues['input']:
            i = queue.get()
            if i is not None:
                self.output_queue.put(i)

    def __init__(self, name="multiplexer", **args):
        """Initializes the module, no arguments required.
        """

        super().__init__(name, **args)
        self._loop_type = 'process'
        self._input_queues['input']._size = -1

middle_modules_class['multiplexer'] = Multiplexer
