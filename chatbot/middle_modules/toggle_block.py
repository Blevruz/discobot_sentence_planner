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
        # Check for block toggle signals first
        block = self._input_queues['block'].get()
        while block is not None:
            self._block = not self._block
            utils.config.debug_print(f"[{self.name}] Toggled blocking: {self._block}")
            block = self._input_queues['block'].get()

        # Process one message from input queue
        out = self.input_queue.get()
        if out is None:
            time.sleep(self.delay)
            return
        
        # If blocking is active, discard the message
        if self._block:
            # utils.config.debug_print(f"[{self.name}] Received data in default queue but blocking, discarding")
            return
        
        # If not blocking, forward the message
        # utils.config.debug_print(f"[{self.name}] Received data in default queue, block: {self._block}, forwarding")
        self.output_queue.put(out)

    def __init__(self, name="toggle_block", **args):
        """Initializes the module.
        """
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'any'
        self._block = args.get('block', False)
        self.delay = args.get('delay', 0.0)
        self._input_queues['block'] = QueueSlot(self, 'input', 'any')

middle_modules_class['toggle_block'] = ToggleBlock
