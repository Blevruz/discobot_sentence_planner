import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

from middle_modules.llm_generate_on_trigger import LLMGenerateOnTrigger
from middle_modules.token_accumulator import GENERATION_DONE


class FakeQueue:
    def __init__(self):
        self.items = []

    def __len__(self):
        return 1

    def put(self, value):
        self.items.append(value)


class FakeEvents:
    def __init__(self, event):
        self.event = event

    def __len__(self):
        return 1

    def get(self):
        event, self.event = self.event, None
        return event


class LLMGenerateOnTriggerTests(unittest.TestCase):
    def test_generation_done_flushes_stream_with_explicit_sentinel(self):
        module = LLMGenerateOnTrigger()
        stream = FakeQueue()
        text = FakeQueue()
        module._output_queues['stream'] = stream
        module._output_queues['text'] = text
        module._input_queues['events'] = FakeEvents({
            'event': 'generation_done',
            'data': {'text': 'Final sentence without punctuation'},
        })

        module.action(0)

        self.assertEqual(stream.items, [GENERATION_DONE])
        self.assertIsNotNone(stream.items[0])
        self.assertEqual(text.items, ['Final sentence without punctuation'])


if __name__ == '__main__':
    unittest.main()
