# chatbot/middle_modules/repeater.py
from middle_modules.dummy import DummyMiddle, middle_modules_class

class Repeater(DummyMiddle):

    def action(self, i):
        self.output_queue.put(self.input_queue.get())

    def __init__(self, name="repeater", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'

middle_modules_class['repeater'] = Repeater

