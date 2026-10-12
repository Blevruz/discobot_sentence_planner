# chatbot/middle_modules/token_accumulator.py
import re

from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config


# TODO make this a config thing
GENERATION_DONE = "\x00__TOKEN_ACCUMULATOR_GENERATION_DONE__\x00"


class TokenAccumulator(DummyMiddle):
    """
    Accumulates incoming tokens into sentence-sized segments.

    Input queue:
        'tokens' : token/chunk strings; GENERATION_DONE flushes the current segment
    Output queue:
        'stream' : emits strings (segments)
    """

    # Common abbreviations which should not cause a sentence flush when the
    # period is the last character of a streamed chunk.
    _ABBREVIATIONS = {
        "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.",
        "st.", "vs.", "etc.", "e.g.", "i.e.", "u.s.", "u.k.",
    }
    _SENTENCE_END_RE = re.compile(r"[.!?](?:[\"'\u2019\u201d\u00bb)]*)\s*$")

    def __init__(self, name="token_accumulator", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'

        # Remove default 'input' slot and define ours
        del self._input_queues['input']
        self._input_queues['tokens'] = QueueSlot(self, 'input', datatype='string')
        self._input_queues['default'] = self._input_queues['tokens']

        self._output_queues['stream'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['default'] = self._output_queues['stream']

        self.sentence_end_tokens = args.get(
            "sentence_end_tokens", ['.', '!', '?', '\n', '\r']
        )
        self.segment = ""

    def _is_end_of_sentence(self, text):
        """Return True when *text* ends at a sentence boundary."""
        if not text:
            return False

        if text.endswith(('\n', '\r')):
            return True

        if not self._SENTENCE_END_RE.search(text):
            return False

        # A terminal period followed by a quote/parenthesis is still a
        # sentence boundary, but a common abbreviation is not.
        stripped = text.rstrip().rstrip('"\'\u2019\u201d\u00bb)')
        if stripped.endswith('.'):
            word = stripped.rsplit(None, 1)[-1].lower()
            if word in self._ABBREVIATIONS:
                return False

        terminal = text.rstrip().rstrip('"\'\u2019\u201d\u00bb)')
        return any(terminal.endswith(token) for token in self.sentence_end_tokens)

    def _emit_segment(self):
        if self.segment and len(self._output_queues['stream']) > 0:
            self._output_queues['stream'].put(self.segment)
            utils.config.debug_print(f"[{self.name}] Emitted segment: {self.segment}")
        self.segment = ""

    def action(self, i):
        q = self.input_queue
        while True:
            token = q.get()
            if token is None:
                # QueueSlot.get() returns None when no token is available yet.
                # That is not an end-of-generation signal: another scheduler
                # iteration may deliver the next token.
                break

            if token == GENERATION_DONE:
                self._emit_segment()
                break

            utils.config.debug_print(f"[{self.name}] Token received: {token}")
            self.segment += token
            utils.config.debug_print(f"[{self.name}] Segment: {self.segment}")

            if self._is_end_of_sentence(self.segment):
                self._emit_segment()


middle_modules_class['token_accumulator'] = TokenAccumulator
