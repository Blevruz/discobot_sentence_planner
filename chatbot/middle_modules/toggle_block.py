# chatbot/middle_modules/toggle_block.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import time

class ToggleBlock(DummyMiddle):
    """Toggleable blocking module
    Handles multiple different input types:
    - input: any
        This input is relayed to the output queue when not blocked
        Otherwise, it is emptied
    - block: signal
        On receiving anything, toggles blocking
    """

    def action(self, i):
        block = self._input_queues['block'][0].get()
        if block is not None:
            self._block = not self._block
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}]Toggled blocking: {self._block}")

        while self._block:
            while True:
                self.input_queue.get()

            time.sleep(0.1)
            return
        else:
            while True:
                out = self.input_queue.get()
                if out is not None:
                    self.output_queue.put(out)

    def __init__(self, name="toggle_block", **args):
        """Initializes the module.
        """
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'any'
        self._block = 0
        self._input_queues['block'] = QueueSlot(self, 'input', 'any')

middle_modules_class['toggle_block'] = ToggleBlock
