# chatbot/middle_modules/llm_stream.py
import requests
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import time
import json

class LLMStream(DummyMiddle):
    """Sends received input to an LLM API and returns the response.
    Handles multiple different input types:
    - Prefix: a string that is added to the message queue and sent with
    the next user input
    - System: a string sent to the LLM as a system message, prompting for
    generation
    - User: the user input, sent to the LLM as a user message, prompting
    for generation
    Has different output types:
    - output: the final output of the LLM
    - stream: the output of the LLM as it is generated
    """

    def action(self, i):
        """Iterates through each queue and calls their respective handlers
        """

        if len(self._input_queues['prefix']) > 0:
            prefix_input = self._input_queues['prefix'][0].get()
            if prefix_input:
                self._handle_prefix_input(prefix_input)

        if len(self._input_queues['system']) > 0:
            system_input = self._input_queues['system'][0].get()
            if system_input:
                self.output_queue.put(self._handle_system_input(system_input))

        user_input = self.input_queue.get()
            if user_input:
            self.output_queue.put(self._handle_user_input(user_input))


    def __init__(self, name="llm_stream", **args):
        """Initializes the module.
        Arguments:
            url : str
                URL of the LLM API
            api : str
                API endpoint of the LLM API, appended to URL during requests
            prompt : str
                Prompt to send to the LLM first
            context: list
                List of dicts containing role and message, representing an
                initial context for the LLM.
            max_tokens : int
                Maximum number of tokens to generate in a single call
            max_tokens_total : int
                Maximum number of tokens to generate over this object's lifetime
                Set to -1 for infinite
            temperature : float
                Temperature of the LLM. Higher values make the LLM more
                creative, lower values make it more conservative.
            language : str
                Language of the LLM. Defaults to English.
        """

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

        self._output_queues['output'] = QueueSlot(self, \
                'output', datatype='string')
        self._output_queues['default'] = self._output_queues['output']
        self._output_queues['stream'] = QueueSlot(self, \
                'output', datatype='string')


        if utils.config.verbose:
            for name, queue in self._input_queues.items():
                utils.config.debug_print(f"[{self.name}]Input queue {name}: {queue.datatype} belongs to {queue._module.name}")

        self._initial_prompt = args.get('prompt', 'You are a friendly robot assistant.  Have a pleasant chat with your interlocutor, and keep your answers short.')
        self._context = args.get('context', [])
        self._max_tokens = args.get('max_tokens', 256)
        self._max_tokens_total = args.get('max_tokens_total', -1)
        self.total_tokens = 0
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


    def call_llm(self, headers, payload, stream=False):

        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Sending request to {self._url}{self._api} with headers {headers} and payload {payload}")

        start_time = time.time()
        resp = requests.post(f"{self._url}{self._api}",
                             headers=headers,
                             json=payload,
                             stream=stream)
        resp.raise_for_status()
        end_time = time.time()
        generation_time = end_time - start_time

        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Received response {resp} with status code {resp.status_code} in {generation_time} seconds")

        if self._max_tokens_total > 0:
            r = resp.json()
            self.total_tokens += r['usage']['total_tokens']
            if self.total_tokens > self._max_tokens_total:
                raise Exception(f"Total tokens {self.total_tokens} exceeded max tokens {self._max_tokens_total}")

        return resp


    def _should_stream(self):
        if len(self._output_queues['stream']) > 0:
            return True
        return False


    def _handle_user_input(self, user_input):
        headers, payload = self.base_prompt
        self.base_prompt[1]["stream"] = self._should_stream()
        if self.prefix_input != "":
            payload['messages'].append({"role": "system", "content": self.prefix_input})
            self.prefix_input = ""
        payload['messages'].append({"role": "user", "content": user_input})
        resp = self.call_llm(headers, payload, stream=self._should_stream())
        assistant_text = self._stream_response(resp)
        payload['messages'].append({
            "role": "assistant",
            "content": assistant_text
        })
        return assistant_text


    def _handle_prefix_input(self, prefix_input):
        self.prefix_input += "\n" + prefix_input


    def _handle_system_input(self, system_input):
        headers, payload = self.base_prompt
        self.base_prompt["stream"] = self._should_stream()
        payload['messages'].append({"role": "system", "content": system_input})
        resp = self.call_llm(headers, payload, stream=self._should_stream())
        assistant_text = self._stream_response(resp)
        payload['messages'].append({
            "role": "assistant",
            "content": assistant_text
        })
        return assistant_text

    def _is_end_of_word_token(self, token):
        return token in [' ', '.', ',', '!', '?', ':', ';', '\n']


    def _stream_response(self, resp):
        full_text = ""
        segment = ""

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]

                if data_str.strip() == "[DONE]":
                    break

                data = json.loads(data_str)
                delta = data["choices"][0].get("delta", {})
                token = delta.get("content")

                if token:
                    full_text += token
                    segment += token
                    if self._is_end_of_word_token(token) and self._should_stream():
                        self._output_queues["stream"][0].put(segment)
                        segment = ""

        return full_text

middle_modules_class['llm_stream'] = LLMStream
