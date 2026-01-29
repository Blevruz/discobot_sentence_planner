# chatbot/middle_modules/length_block.py

from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config


class LengthBlock(DummyMiddle):
    """Blocks strings that do not meet length requirements.

    Inputs:
    - default: string
        String to validate

    Outputs:
    - default: string
        Forwarded only if length is valid
    """

    def __init__(self, name="length_block", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'

        # Configurable limits
        self.min_len = args.get("min_len", 1)
        self.max_len = args.get("max_len", 200)

        if utils.config.verbose:
            utils.config.debug_print(
                f"[{self.name}] LengthBlock initialized (min={self.min_len}, max={self.max_len})"
            )

    def action(self, i):
        while True:
            item = self.input_queue.get()
            if item is None:
                return

            if not isinstance(item, str):
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}][{self.name}] Dropped non-string input: {item}")
                continue

            length = len(item.strip())

            if self.min_len <= length <= self.max_len:
                self.output_queue.put(item)
            else:
                if utils.config.verbose:
                    utils.config.debug_print(
                        f"[{self.name}] Blocked string (len={length}): '{item}'"
                    )


middle_modules_class['length_block'] = LengthBlock

