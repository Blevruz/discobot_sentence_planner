import pickle
import sys
import time
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

from middle_modules.buffer import Buffer
from middle_modules.dummy import DummyMiddle
from middle_modules.token_accumulator import GENERATION_DONE, TokenAccumulator
from utils.dummy_module import DummyModule
from utils.queues import END_OF_TURN, ControlMessage, QueueSlot, QueueWrapper


class Recorder(DummyModule):
    """Sink recording everything its action() code gets to see."""

    def __init__(self, name="recorder", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.seen = []

    def action(self, i):
        item = self.input_queue.get()
        if item is None:
            time.sleep(0.001)
        else:
            self.seen.append(item)


class SlowUpper(DummyMiddle):
    """Stream transformer standing in for the lapsus filters: it takes its
    time and rewrites the text, so that anything not travelling in-band
    behind its output would arrive first."""

    def __init__(self, name="slow_upper", delay=0.05, **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.delay = delay
        self.forward_control('input', 'output')

    def action(self, i):
        text = self.input_queue.get()
        if text is None:
            time.sleep(0.001)
            return
        time.sleep(self.delay)
        self.output_queue.put(text.upper())


def stop_all(modules):
    """Stop every loop before any module cleans up the queues it shares with
    its neighbours (which would raise in a neighbour still polling)."""
    for m in modules:
        m.stopped.set()
    for m in modules:
        loop = getattr(m, "loop", None)
        if loop is not None:
            loop.join(timeout=2)
    for m in modules:
        m.stop_loop()


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


def slot_with_queue(module):
    """Input slot of `module` fed by a queue bound to a bare source module."""
    source = DummyModule("source")
    source.link_to(module)
    return source.output_queue, module.input_queue


class ControlMessageTests(unittest.TestCase):
    def test_equality_and_pickling(self):
        self.assertEqual(END_OF_TURN, ControlMessage("end_of_turn"))
        self.assertNotEqual(END_OF_TURN, ControlMessage("other"))
        self.assertNotEqual(END_OF_TURN, "end_of_turn")
        self.assertEqual(pickle.loads(pickle.dumps(END_OF_TURN)), END_OF_TURN)


class QueueSlotPolicyTests(unittest.TestCase):
    def test_control_messages_are_swallowed_by_default(self):
        module = DummyModule("plain")
        out, slot = slot_with_queue(module)
        for item in ["a", END_OF_TURN, "b", END_OF_TURN]:
            out.put(item)
        time.sleep(0.1)  # multiprocessing queues are fed by a thread
        got = [slot.get(), slot.get(), slot.get()]
        self.assertEqual(got, ["a", "b", None])

    def test_forward_keeps_control_message_behind_the_data(self):
        module = DummyModule("relay")
        module.forward_control('input', 'output')
        sink = DummyModule("sink")
        module.link_to(sink)
        out, slot = slot_with_queue(module)
        for item in ["a", END_OF_TURN]:
            out.put(item)
        time.sleep(0.1)
        # The module processes "a" and emits its result...
        self.assertEqual(slot.get(), "a")
        module.output_queue.put("A")
        # ...and only then reads the message, which gets relayed behind it.
        self.assertIsNone(slot.get())
        time.sleep(0.1)
        self.assertEqual(sink.input_queue.get(), "A")
        # The sink does not deliver control messages: it swallows it.
        self.assertIsNone(sink.input_queue.get())

    def test_deliver_hands_the_message_to_the_module(self):
        module = DummyModule("aware")
        module.deliver_control()
        out, slot = slot_with_queue(module)
        out.put("a")
        out.put(END_OF_TURN)
        time.sleep(0.1)
        self.assertEqual([slot.get(), slot.get(), slot.get()],
                         ["a", END_OF_TURN, None])

    def test_forward_to_unknown_slot_is_an_error(self):
        module = DummyModule("bad")
        with self.assertRaises(ValueError):
            module.forward_control('input', 'no_such_slot')


class AssistantTurnPipelineTests(unittest.TestCase):
    """token_accumulator -> [transformer] -> buffer, as in llm*.json."""

    def build(self, transformer=None):
        self.source = DummyModule("tokens_in")
        self.acc = TokenAccumulator()
        self.acc._loop_type = 'thread'   # no processes in unit tests
        self.buf = Buffer("assistant_buffer",
                          datatype_in="string", datatype_out="string")
        self.rec = Recorder("assistant_append")

        chain = [self.acc] + ([transformer] if transformer else []) \
            + [self.buf, self.rec]
        self.source.link_to(self.acc, to_slot='tokens')
        for a, b in zip(chain, chain[1:]):
            a.link_to(b, from_slot='stream' if a is self.acc else 'default')
        self.modules = chain
        for m in chain:
            m.start_loop()
        self.addCleanup(self.stop)

    def stop(self):
        stop_all(self.modules)

    def generate(self, *tokens):
        for t in tokens:
            self.source.output_queue.put(t)
        self.source.output_queue.put(GENERATION_DONE)

    def test_turn_is_flushed_whole_without_transformer(self):
        self.build()
        self.generate("Hello", " world.", " How", " are", " you?")
        self.assertTrue(wait_for(lambda: self.rec.seen))
        self.assertEqual(self.rec.seen, ["Hello world. How are you?"])

    def test_turns_do_not_spill_into_each_other_through_slow_transformer(self):
        self.build(SlowUpper())
        self.generate("One.", " Two.", " Three.")
        self.generate("Four.", " Five")  # unpunctuated tail, emitted on DONE
        self.assertTrue(wait_for(lambda: len(self.rec.seen) >= 2))
        time.sleep(0.3)  # nothing else may show up
        self.assertEqual(self.rec.seen, ["ONE. TWO. THREE.", "FOUR. FIVE"])

    def test_no_control_message_leaks_into_modules(self):
        self.build(SlowUpper())
        self.generate("Hi.")
        self.assertTrue(wait_for(lambda: self.rec.seen))
        self.assertTrue(all(isinstance(x, str) for x in self.rec.seen))


@unittest.skipIf(sys.version_info < (3, 8), "needs unittest.mock")
class EnglishLapsusRelayTests(unittest.TestCase):
    def test_english_lapsus_relays_end_of_turn_behind_its_text(self):
        # The real EnglishBrain needs nltk/Levenshtein and a FastText model;
        # a stub is enough here since no lapsus is applied (proba 0).
        try:
            import utils.englishcerveau  # noqa: F401
        except ImportError:
            stub = types.ModuleType("utils.englishcerveau")
            stub.EnglishBrain = lambda *a, **k: types.SimpleNamespace(
                est_mot_interessant=lambda w: False)
            sys.modules["utils.englishcerveau"] = stub
        from middle_modules.english_lapsus import EnglishLapsus

        src = DummyModule("src")
        lapsus = EnglishLapsus(proba_lapsus=0.0)
        buf = Buffer("buf", datatype_in="string", datatype_out="string")
        rec = Recorder("rec")
        src.link_to(lapsus)
        lapsus.link_to(buf)
        buf.link_to(rec)
        modules = [lapsus, buf, rec]
        for m in modules:
            m.start_loop()
        try:
            for item in ["First sentence.", "Second one.", END_OF_TURN]:
                src.output_queue.put(item)
            self.assertTrue(wait_for(lambda: rec.seen))
            # english_lapsus strips each segment, so compare ignoring spaces
            self.assertEqual("".join(rec.seen[0].split()),
                             "Firstsentence.Secondone.")
        finally:
            stop_all(modules)


if __name__ == '__main__':
    unittest.main()
