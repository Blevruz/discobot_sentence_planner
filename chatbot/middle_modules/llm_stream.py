# chatbot/middle_modules/llm_stream.py
from middle_modules.llm import LLMRequest
import time
import json
import aiohttp
import asyncio

raise NotImplementedError, "Not implemented yet"

class LLMStream(LLMRequest):
    """Sends received input to an LLM API and returns the response in two
    queues, one at the end and another while the generation is in progress.
    Handles multiple different input types:
    - prefix: a string that is added to the message queue and sent with
    the next user input
    - system: a string sent to the LLM as a system message, prompting for
    generation
    - user: the user input, sent to the LLM as a user message, prompting
    for generation
    Multiple outputs:
    - output: the final output of the LLM
    - stream: the output of the LLM as it is generated
    """


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
        LLMRequest.__init__(self, name, **args)

    def make_base_prompt(self):
        headers, payload = LLMRequest.make_base_prompt(self)
        payload["stream"] = True
        return headers, payload


middle_modules_class['llm_request'] = LLMRequest
