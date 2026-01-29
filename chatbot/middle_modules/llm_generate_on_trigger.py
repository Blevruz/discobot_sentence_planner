# middle_modules/llm_generate_on_trigger.py
import uuid
from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
import utils.config

middle_modules_class = {}

class LLMGenerateOnTrigger(DummyModule):
    def __init__(self, name="llm_generate_on_trigger", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.active = False

        self._input_queues['trigger'] = QueueSlot(self, 'input', datatype='dict')
        self._input_queues['events'] = QueueSlot(self, 'input', datatype='dict')

        self._output_queues['cmd'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['text_out'] = QueueSlot(self, 'output', datatype='string')

        self.buffer = ""

    def action(self, i):
        # Start generation
        if len(self._input_queues['trigger']) > 0:
            if not self.active:
                t = self._input_queues['trigger'][0].get()
                if t:
                    if utils.config.verbose:
                        utils.config.debug_print(f"[{self.name}] Starting generation")
                    cmd = {
                        "id": str(uuid.uuid4()),
                        "from": self.name,
                        "op": "GENERATE",
                        "payload": {}
                    }
                    self.active = True
                    self.buffer = ""
                    self._output_queues['cmd'][0].put(cmd)

        # Handle streaming tokens
        if len(self._input_queues['events']) > 0:
            evt = self._input_queues['events'][0].get()
            if evt:
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}] Event received: {evt}")

                if evt.get("event") == "token":
                    self.buffer += evt["data"]["text"]

                elif evt.get("event") == "generation_done":
                    self.buffer = evt["data"]["text"]
                    if utils.config.verbose:
                        utils.config.debug_print(f"[{self.name}] Generation done: {self.buffer}")
                    self._output_queues['text_out'][0].put(self.buffer)
                    self.active = False

middle_modules_class['llm_generate_on_trigger'] = LLMGenerateOnTrigger

