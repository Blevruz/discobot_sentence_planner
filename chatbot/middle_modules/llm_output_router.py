# chatbot/middle_modules/llm_output_router.py

from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
import utils.config

middle_modules_class = {}

class LLMOutputRouter(DummyModule):
    def __init__(self, name="llm_output_router", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'

        self._input_queues['input'] = QueueSlot(self, 'input', datatype='dict')

        self._output_queues['text'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['control'] = QueueSlot(self, 'output', datatype='dict')

    def action(self, i):
        if self.input_queue.empty():
            return

        msg = self.input_queue.get()

        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}] Routing message: {msg}")

        if msg.get("type") == "event":
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}] -> text")
            self._output_queues['text'][0].put(msg)

        elif msg.get("type") == "response":
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}] -> control")
            self._output_queues['control'][0].put(msg)

middle_modules_class['llm_output_router'] = LLMOutputRouter

