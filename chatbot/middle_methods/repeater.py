# chatbot/middle_methods/repeater.py
from middle_methods.dummy import DummyMiddle, middle_methods_class

class Repeater(DummyMiddle):

    def action(self, i):
        self.output_queue.put(self.input_queue.get())

    def __init__(self, name="repeater"):
        DummyMiddle.__init__(self, name)
        self._input_queues = []
        self._output_queues = []
        self._loop_type = 'process'

middle_methods_class['repeater'] = Repeater

