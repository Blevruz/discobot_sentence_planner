# chatbot/utils/llm_service/generator.py
import requests
import json

class LLMGenerator:
    def __init__(self, url, api, headers, temperature, max_tokens):
        self.url = url
        self.api = api
        self.headers = headers
        self.temperature = temperature
        self.max_tokens = max_tokens

    def build_payload(self, context):
        return {
            "messages": [{"role": m["role"], "content": m["content"]} for m in context],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }

    def stream_generate(self, context):
        payload = self.build_payload(context)
        resp = requests.post(self.url + self.api, headers=self.headers, json=payload, stream=True)
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            chunk = json.loads(data)
            token = chunk["choices"][0].get("delta", {}).get("content")
            if token:
                yield token

