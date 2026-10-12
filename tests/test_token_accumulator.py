import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

from middle_modules.token_accumulator import GENERATION_DONE, TokenAccumulator


class FakeInput:
    def __init__(self, values):
        self.values = iter(values)

    def get(self):
        return next(self.values, None)


class FakeOutput:
    def __init__(self):
        self.items = []

    def __len__(self):
        return 1

    def put(self, value):
        self.items.append(value)


class TokenAccumulatorTests(unittest.TestCase):
    def make_accumulator(self, tokens):
        acc = TokenAccumulator()
        acc._input_queues['default'] = FakeInput(tokens)
        output = FakeOutput()
        acc._output_queues['stream'] = output
        return acc, output

    def test_tokens_are_accumulated_across_scheduler_iterations(self):
        acc = TokenAccumulator()
        output = FakeOutput()
        acc._output_queues['stream'] = output

        # Simulate the real QueueSlot: an empty queue returns None, but that
        # does not mean generation has finished.
        class IteratingInput:
            def __init__(self):
                self.values = iter(["Hi there", None, "!", None])

            def get(self):
                return next(self.values)

        acc._input_queues['default'] = IteratingInput()

        acc.action(0)
        self.assertEqual(output.items, [])

        acc.action(1)
        self.assertEqual(output.items, ["Hi there!"])

    def test_quotation_mark_does_not_cut_off_sentence(self):
        acc, output = self.make_accumulator(['He said, "', 'hello', ' world', '."'])
        acc.action(0)
        self.assertEqual(output.items, ['He said, "hello world."'])

    def test_colon_does_not_cut_off_sentence(self):
        acc, output = self.make_accumulator(['The answer is:', ' forty-two.'])
        acc.action(0)
        self.assertEqual(output.items, ['The answer is: forty-two.'])

    def test_common_abbreviation_does_not_cut_off_sentence(self):
        acc, output = self.make_accumulator(['Dr.', ' Smith arrived.'])
        acc.action(0)
        self.assertEqual(output.items, ['Dr. Smith arrived.'])

    def test_normal_sentence_end_is_emitted(self):
        acc, output = self.make_accumulator(['Hello', ' world. ', 'Next sentence!'])
        acc.action(0)
        self.assertEqual(output.items, ['Hello world. ', 'Next sentence!'])

    def test_generation_end_flushes_unpunctuated_sentence(self):
        acc, output = self.make_accumulator(['This is the final sentence', GENERATION_DONE])
        acc.action(0)
        self.assertEqual(output.items, ['This is the final sentence'])

    def test_none_does_not_flush_unpunctuated_sentence(self):
        acc, output = self.make_accumulator(['This is still being generated'])
        acc.action(0)
        self.assertEqual(output.items, [])

    def test_doesnt_cut_off_numbers(self):
        acc, output = self.make_accumulator(['This', ' sentence', ' contains', ' 5', ' different', ' numbers', ' and', ' 1 of', ' them is 4', ' while 2 are 1!'])
        acc.action(0)
        self.assertEqual(output.items, ['This sentence contains 5 different numbers and 1 of them is 4 while 2 are 1!'])


if __name__ == '__main__':
    unittest.main()
