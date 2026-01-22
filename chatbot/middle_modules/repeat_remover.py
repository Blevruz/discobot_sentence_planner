# chatbot/middle_modules/repeat_remover.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueWrapper, QueueSlot
import utils.config

import Levenshtein

# We don't pass on any input that is too similar to any previous input

class RepeatRemover(DummyMiddle):

    def __init__(self, name="repeat_remover", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'
        self._input_queues['muted'] = QueueSlot(self, 'input', datatype='string')
        self.datatype_out = 'string'
        self.threshold = args.get('threshold', 0.8)
        self.memory = []
        if utils.config.verbose:
            for name, queue in self._input_queues.items():
                utils.config.debug_print(f"Input queue {name}: {queue.datatype} belongs to {queue._module.name}")

    def action(self, i):
        if len(self._input_queues['muted']) > 0:
            for m in self._input_queues['muted']:
                while not m.empty():
                    self.memory.append(m.get())

        if not self.input_queue.empty():
            text = self.input_queue.get()
            # If we have previous inputs stored:
            if len(self.memory) > 0:
                # We check if current input is too similar to any previous input
                for m in self.memory:
                    ratio = Levenshtein.ratio(text, m)
                    if utils.config.verbose:
                        utils.config.debug_print(f"Ratio between {m} and {text}: {ratio}")
                    if ratio > self.threshold:
                        # If so, we discard it
                        return
            # If we reach this point, we add the input to the memory
            self.memory.append(text)
            self.output_queue.put(text)


middle_modules_class['repeat_remover'] = RepeatRemover
