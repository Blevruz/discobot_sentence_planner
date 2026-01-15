# chatbot/middle_modules/llm_stream.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import time
import json
import aiohttp
import asyncio

raise NotImplementedError, "Not implemented yet"

class LLMStream(DummyMiddle):

    def action(self, i):
        if not self.input_queue.empty():
            user_input = self.input_queue.get()
            headers, payload = self.base_prompt
            payload['messages'].append({"role": "user", "content": user_input})
            start_time = time.time()
            resp = requests.post(f"{self._url}{self._api}", headers=headers, json=payload)
            resp.raise_for_status()
            end_time = time.time()
            generation_time = end_time - start_time
            data = resp.json()
            payload['messages'].append({"role": "assistant", "content": data['choices'][0]['message']['content']})
            self.output_queue.put(f"GENERATION TIME: {generation_time}, \"{data['choices'][0]['message']['content']}\"")


    def __init__(self, name="llm_request", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self._initial_prompt = args.get('prompt', 'You are a friendly robot assistant.  Have a pleasant chat with your interlocutor, and keep your answers short.')
        self._max_tokens = args.get('max_tokens', 256)
        self._temperature = args.get('temperature', 0.3)
        self._language = args.get('language', 'fr')
        
        self._url = args.get('url', 'http://localhost:8000')
        self._api = args.get('api', '/v1/chat/completions')
        self._headers = args.get('headers', {'Content-Type': 'application/json'})
        self._token = args.get('token', None)
        self.base_prompt = self.make_base_prompt()

    def make_base_prompt(self):
        headers = {
            'Content-Type': 'application/json'
            }
        payload = {
                "messages": [],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stream": True
                }

        payload['messages'].append({"role": "developer", "content": self._initial_prompt})
        return headers, payload


middle_modules_class['llm_request'] = LLMRequest
