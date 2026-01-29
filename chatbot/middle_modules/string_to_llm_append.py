# chatbot/middle_modules/string_to_llm_append.py
import uuid
from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
import utils.config

middle_modules_class = {}

class StringToLLMAppend(DummyModule):
    def __init__(self, name="string_to_llm_append", role="user", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.role = role
        self.pending = {}

        self._input_queues['text'] = QueueSlot(self, 'input', datatype='string')
        self._input_queues['control'] = QueueSlot(self, 'input', datatype='dict')

        self._output_queues['cmd'] = QueueSlot(self, 'output', datatype='dict')
        self._output_queues['trigger'] = QueueSlot(self, 'output', datatype='dict')

    def action(self, i):
        # Handle LLM responses
        if len(self._input_queues['control']) > 0:
            resp = self._input_queues['control'][0].get()
            if resp is not None:
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}] Got control response: {resp}")
                if resp.get("type") == "response" and resp["id"] in self.pending:
                    if utils.config.verbose:
                        utils.config.debug_print(f"[{self.name}] Append confirmed, triggering generatsion.")
                    if len(self._output_queues['trigger']) > 0:
                        self._output_queues['trigger'][0].put({
                            "type": "trigger",
                            "reason": "append_done",
                            "cmd_id": resp["id"]
                        })
                        del self.pending[resp["id"]]
                    else:
                        raise Exception(f"Module {self.name} has no trigger output queue")
        else:
            raise Exception(f"Module {self.name} has no control queue")

        # Handle new strings
        if len(self._input_queues['text']) > 0:
            text = self._input_queues['text'][0].get()
            if text is not None:
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}] New text received: {text}")
                cmd_id = str(uuid.uuid4())

                cmd = {
                    "id": cmd_id,
                    "from": self.name,
                    "op": "APPEND",
                    "payload": {
                        "messages": [{
                            "role": self.role,
                            "content": text
                        }]
                    }
                }

                self.pending[cmd_id] = True
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}] Sending APPEND command: {cmd}")
                if len(self._output_queues['cmd']) > 0:
                    self._output_queues['cmd'][0].put(cmd)
                else:
                    raise Exception(f"Module {self.name} has no cmd output queue")
        else:
            raise Exception(f"Module {self.name} has no input queue")

middle_modules_class['string_to_llm_append'] = StringToLLMAppend

