# chatbot/middle_modules/time_block.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import time

class TimeBlock(DummyMiddle):
    """Blocks for a given amount of time.
    Handles multiple different input types:
    - input: any
        This input is relayed to the output queue when not blocked
        Otherwise, it is emptied
    - block: int
        The amount of time to block for, in seconds
    """

    def action(self, i):
        block = self._input_queues['block'][0].get()
        if block is not None:
            self._block_time = block
            self._start_time = time.time()

        while time.time() - self._start_time < self._block_time:
            while True:
                self.input_queue.get()
            time.sleep(0.1)
            return

    def __init__(self, name="time_block", **args):
        """Initializes the module.
        """
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'any'
        self._block_time = 0
        self._start_time = time.time()
        self._input_queues['block'] = QueueSlot(self, 'input', 'int')

middle_modules_class['time_block'] = TimeBlock
