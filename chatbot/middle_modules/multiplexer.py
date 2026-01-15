# chatbot/middle_modules/multiplexer.py
from middle_modules.dummy import DummyMiddle, middle_modules_class

class Multiplexer(DummyMiddle):

    def action(self, i):
        #self.output_queue.put(self.input_queue.get())
        # check if any of the input queues are not empty
        for queue in self._input_queues['input']:
            if not queue.empty():
                self.output_queue.put(queue.get())

    def __init__(self, name="multiplexer", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self._input_queues['input']._size = -1

middle_modules_class['multiplexer'] = Multiplexer
