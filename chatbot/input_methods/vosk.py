from input_methods.dummy import DummyInput, input_methods_class
from pathlib import Path
import multiprocessing
import vosk
import pyaudio
import json


class VoskInput(DummyInput):
    def __init__(self, name, model_path):
        self.name = name
        self.input_loop = multiprocessing.Process(target=self._input_loop)
        self.model = vosk.Model(model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        # A lot of arbitrary values in there.
        # TODO: test varying these
        self.audio_stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)

    def _input_loop(self):
        while True:
            data = self.audio_stream.read(4096)
            if self.rec.AcceptWaveform(data):
                result = self.rec.Result()
                text = json.loads(result)['text']
                self.queue.put(text)


BASE_DIR = Path(__file__).parent
VOSK_MODEL_PATH_FR = str(BASE_DIR / ".." / ".."/ "models" / "vosk" / "fr")
VOSK_MODEL_PATH_EN = str(BASE_DIR / ".." / ".." / "models" / "vosk" / "en")
input_methods_class = dict()
input_methods_class['vosk'] = lambda name: VoskInput(name, VOSK_MODEL_PATH_EN)

