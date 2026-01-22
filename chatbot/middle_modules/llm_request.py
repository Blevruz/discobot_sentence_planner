# chatbot/middle_modules/llm_request.py
import requests
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import time

class LLMRequest(DummyMiddle):

    def action(self, i):

        if len(self._input_queues['prefix']) > 0:
            if not self._input_queues['prefix'][0].empty():
                prefix_input = self._input_queues['prefix'][0].get()
                self._handle_prefix_input(prefix_input)

        if len(self._input_queues['system']) > 0:
            if not self._input_queues['system'][0].empty():
                system_input = self._input_queues['system'][0].get()
                self.output_queue.put(self._handle_system_input(system_input))

        if not self.input_queue.empty():
            user_input = self.input_queue.get()
            self.output_queue.put(self._handle_user_input(user_input))


    def __init__(self, name="llm_request", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'

        del self._input_queues['input']
        self._input_queues['user'] = QueueSlot(self, \
                'input', datatype='string')
        self._input_queues['default'] = self._input_queues['user']
        self._input_queues['prefix'] = QueueSlot(self, \
                'input', datatype='string')
        self._input_queues['system'] = QueueSlot(self, \
                'input', datatype='string')

        if utils.config.verbose:
            for name, queue in self._input_queues.items():
                utils.config.debug_print(f"Input queue {name}: {queue.datatype} belongs to {queue._module.name}")

        self._initial_prompt = args.get('prompt', 'You are a friendly robot assistant.  Have a pleasant chat with your interlocutor, and keep your answers short.')
        self._context = args.get('context', [])
        self._max_tokens = args.get('max_tokens', 256)
        self._temperature = args.get('temperature', 0.3)
        self._language = args.get('language', 'en')
        self._url = args.get('url', 'http://localhost:8000')
        self._api = args.get('api', '/v1/chat/completions')
        self._headers = args.get('headers', {'Content-Type': 'application/json'})
        self._token = args.get('token', None)
        self.base_prompt = self.make_base_prompt()
        self.prefix_input = ""

    def make_base_prompt(self):
        headers = {
            'Content-Type': 'application/json'
            }
        payload = {
                "messages": [],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stream": False
                }

        payload['messages'].append({"role": "developer", "content": self._initial_prompt})
        for c in self._context:
            payload['messages'].append({"role": c["role"], "content": c["content"]})
        return headers, payload

    def _handle_user_input(self, user_input):
        headers, payload = self.base_prompt
        if self.prefix_input != "":
            payload['messages'].append({"role": "system", "content": self.prefix_input})
            self.prefix_input = ""
        payload['messages'].append({"role": "user", "content": user_input})
        start_time = time.time()
        resp = requests.post(f"{self._url}{self._api}", headers=headers, json=payload)
        resp.raise_for_status()
        end_time = time.time()
        generation_time = end_time - start_time
        data = resp.json()
        payload['messages'].append({"role": "assistant", "content": data['choices'][0]['message']['content']})
        #self.output_queue.put(f"\"{data['choices'][0]['message']['content']}\"")
        return data['choices'][0]['message']['content']

    def _handle_prefix_input(self, prefix_input):
        self.prefix_input.append("\nprefix_input")


    def _handle_system_input(self, system_input):
        headers, payload = self.base_prompt
        payload['messages'].append({"role": "system", "content": system_input})
        start_time = time.time()
        resp = requests.post(f"{self._url}{self._api}", headers=headers, json=payload)
        resp.raise_for_status()
        end_time = time.time()
        generation_time = end_time - start_time
        payload['messages'].append({"role": "assistant", "content": resp.json()['choices'][0]['message']['content']})
        return resp.json()['choices'][0]['message']['content']


middle_modules_class['llm_request'] = LLMRequest
