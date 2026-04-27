from io import BytesIO
import wave
from middle_modules.dummy import DummyMiddle, middle_modules_class
import requests
import utils.config

class ElevenLabSTT(DummyMiddle):
    def __init__(self, name="elevenlab_stt", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "string"
        self.api_key = args.get("api_key", "")
        self.model = args.get("model", "whisper-1")
        self.endpoint = args.get("endpoint", "https://api.elevenlabs.io/v1/speech-to-text")
        self.rate = args.get("rate", 16000)
        self.channels = args.get("channels", 1)
        self.sample_width = args.get("sample_width", 2)

    def action(self, i):
        audio_data = self.input_queue.get()
        if not audio_data:
            return

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.rate)
            wf.writeframes(audio_data)

        buffer.seek(0)
        headers = {"xi-api-key": self.api_key}
        files = {"file": ("audio.wav", buffer.read(), "audio/wav")}
        data = {"model_id": "scribe_v1"}#self.model}
        response = requests.post(self.endpoint, headers=headers, files=files, data=data)
        response.raise_for_status()

        text = response.json().get("text") or response.json().get("transcript") or ""

        utils.config.debug_print(f"[{self.name}] Received {response} containing {response.json()}")

        if text:
            self.output_queue.put(text)

middle_modules_class["elevenlab_stt"] = ElevenLabSTT

