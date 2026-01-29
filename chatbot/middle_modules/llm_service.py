# chatbot/middle_modules/llm_service.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot

from middle_modules._llm_service.context_store import ContextStore
from middle_modules._llm_service.generator import LLMGenerator
from middle_modules._llm_service.dispatcher import CommandDispatcher

import utils.config


class LLMService(DummyMiddle):
    def __init__(self, name="llm_service", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'

        del self._input_queues['input']
        self._input_queues['cmd'] = QueueSlot(self, 'input', datatype='dict')
        self._input_queues['default'] = self._input_queues['cmd']

        self.ctx = ContextStore(args.get("context", []))
        self.gen = LLMGenerator(
            args.get("url"),
            args.get("api", "/v1/chat/completions"),
            args.get("headers", {"Content-Type": "application/json"}),
            args.get("temperature", 0.3),
            args.get("max_tokens", 256)
        )
        self.dispatcher = CommandDispatcher(self.ctx, self.gen)

    def action(self, i):
        q = self.input_queue

        cmd = q.get()
        if not cmd:
            return
        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}] Received command: {cmd}")

        out_q = self.output_queue
        for r in self.dispatcher.handle(cmd):
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}] Emitting: {r}")
            if type(r) is list:
                for ri in r:
                    out_q.put(ri)
            else:
                out_q.put(r)
        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}] Finished processing cmd {cmd}")

middle_modules_class['llm_service'] = LLMService

