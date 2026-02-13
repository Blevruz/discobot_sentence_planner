# chatbot/middle_modules/token_accumulator.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config


class TokenAccumulator(DummyMiddle):
    """
    Accumulates incoming tokens into segments and emits them
    whenever an end-of-word token is seen.

    Input queue:
        'tokens' : expects individual token strings
    Output queue:
        'stream' : emits strings (segments)
    """

    def __init__(self, name="token_accumulator", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'

        # Remove default 'input' slot and define ours
        del self._input_queues['input']
        self._input_queues['tokens'] = QueueSlot(self, 'input', datatype='string')
        self._input_queues['default'] = self._input_queues['tokens']

        self._output_queues['stream'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['default'] = self._output_queues['stream']

        self.segment = ""
        self.verbose = args.get("verbose", False)

    def _is_end_of_word_token(self, token):
        return token in [' ', '.', ',', '!', '?', ':', ';', '\n']

    def action(self, i):
        q = self.input_queue
        while True:
            token = q.get()
            if token is None:
                break  # no more tokens for now

            self.segment += token

            if self._is_end_of_word_token(token):
                # Emit segment and reset
                if len(self._output_queues['stream']) > 0:
                    self._output_queues['stream'][0].put(self.segment)
                    if self.verbose:
                        utils.config.debug_print(f"[{self.name}] Emitted segment: {self.segment}")
                self.segment = ""


middle_modules_class['token_accumulator'] = TokenAccumulator

