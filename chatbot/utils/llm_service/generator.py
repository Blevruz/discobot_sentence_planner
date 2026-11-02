# chatbot/utils/llm_service/generator.py
import requests
import json
import codecs
import utils.config

class LLMGenerator:
    def __init__(self, url, api, headers, 
                 temperature, max_tokens, 
                 stop_event=None, name="llm_generator"):
        self.url = url
        self.api = api
        self.headers = headers
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._stop_event = stop_event
        self.name = name

    def build_payload(self, context):
        return {
            "messages": [{"role": m["role"], "content": m["content"]} for m in context],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }

    def _should_stop(self):
        if self._stop_event is None:
            return 0
        return self._stop_event.is_set()

    def stream_generate(self, context):
        payload = self.build_payload(context)
        resp = requests.post(self.url + self.api, headers=self.headers, json=payload, stream=True, timeout=(5,30))
        resp.raise_for_status()

        decoder = codecs.getincrementaldecoder("utf-8")()
        buffer = ''
        try:
            # using iter_content to avoid splitting unicode
            for chunk in resp.iter_content(chunk_size=None):
                # action shutdown in case of interruption
                if self._should_stop():
                    break
                buffer += decoder.decode(chunk)
                while '\n' in buffer:
                    raw_line, buffer = buffer.split('\n', 1)
                    line = raw_line.rstrip('\r')

                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    chunk_json = json.loads(data)
                    token = chunk_json["choices"][0].get("delta", {}).get("content")
                    if token:
                        yield token
        finally:
            utils.config.debug_print(f"[{self.name}] Generator received stop event...")
            resp.close()

