# middle_modules/llm_generate_on_trigger.py
import uuid
from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
import utils.config

middle_modules_class = {}

class LLMGenerateOnTrigger(DummyModule):
    """Sends received input to an LLM API and returns the response.
    """


    def __init__(self, name="llm_generate_on_trigger", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.active = False

        self._input_queues['trigger'] = QueueSlot(self, 'input', datatype='dict')
        self._input_queues['events'] = QueueSlot(self, 'input', datatype='dict')

        self._output_queues['cmd'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['text'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['stream'] = QueueSlot(self, 'output', datatype='string')

        self.buffer = ""

    def action(self, i):
        # Start generation
        if len(self._input_queues['trigger']) > 0:
            if not self.active:
                t = self._input_queues['trigger'].get()
                if t:
                    utils.config.debug_print(f"[{self.name}] Received {t}, starting generation")
                    cmd = {
                        "id": str(uuid.uuid4()),
                        "from": self.name,
                        "op": "GENERATE",
                        "payload": {}
                    }
                    self.active = True
                    self.buffer = ""
                    self._output_queues['cmd'].put(cmd)

        # Handle streaming tokens
        if len(self._input_queues['events']) > 0:
            evt = self._input_queues['events'].get()
            if evt:
                utils.config.debug_print(f"[{self.name}] Event received: {evt}")

                if evt.get("event") == "token" and len(self._output_queues['stream']) > 0:
                     utils.config.debug_print(f"[{self.name}] Token received: {evt['data']['text']}")
                     self._output_queues['stream'].put(evt["data"]["text"])

                if evt.get("event") == "generation_done":
                    self.active = False
                    self.buffer = evt["data"]["text"]
                    utils.config.debug_print(f"[{self.name}] Generation done: {self.buffer}")
                    if len(self._output_queues['text']) > 0:
                        self._output_queues['text_out'].put(self.buffer)
                utils.config.debug_print(f"[{self.name}] Finished processing evt {evt}")


middle_modules_class['llm_generate_on_trigger'] = LLMGenerateOnTrigger

