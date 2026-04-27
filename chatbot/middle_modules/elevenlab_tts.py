from io import BytesIO
import wave
from middle_modules.dummy import DummyMiddle, middle_modules_class
import requests

class ElevenLabTTS(DummyMiddle):
    def __init__(self, name="elevenlab_tts", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "string"
        self.datatype_out = "audio"
        self.api_key = args.get("api_key", "")
        self.voice = args.get("voice", "alloy")
        self.model = args.get("model", "eleven_monolingual_v1")
        self.endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}"

    def action(self, i):
        text = self.input_queue.get()
        if not text:
            return

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav"
        }
        payload = {"text": text, "model": self.model}
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()

        wav_bytes = response.content
        with wave.open(BytesIO(wav_bytes), "rb") as wf:
            frames = wf.readframes(wf.getnframes())

        self.output_queue.put(frames)

middle_modules_class["elevenlab_tts"] = ElevenLabTTS