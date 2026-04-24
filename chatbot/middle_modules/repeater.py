# chatbot/middle_modules/repeater.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.config

class Repeater(DummyMiddle):
    """Repeats the input queue to the output queue.
    """

    def action(self, i):
        var = self.input_queue.get()
        if var:
            utils.config.debug_print(f"[{self.name}] Repeating {var}")
            self.output_queue.put(var)

    def __init__(self, name="repeater", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'

middle_modules_class['repeater'] = Repeater

