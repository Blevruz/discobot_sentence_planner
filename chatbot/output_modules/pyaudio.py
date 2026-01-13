# chatbot/output_modules/pyaudio.py
from output_modules.dummy import DummyOutput, output_modules_class
from utils.config import verbose
import pyaudio

class PyAudioOutput(DummyOutput):

    def action(self, i):
        self._stream.write(self.input_queue.get())

    def __init__(self, name="pyaudio_output", **args):
        DummyOutput.__init__(self, name)
        self._loop_type = "process"
        self._datatype_in = "audio"
        self._datatype_out = "audio"
        self.format = args.get('format', pyaudio.paInt16)
        self.channels = args.get('channels', 1)
        self.rate = args.get('rate', 16000)
        self.frames_per_buffer = args.get('frames_per_buffer', 48000)
        self.args = args
        self.pyaudio = None
        self._stream = None

    def module_start(self):
        self.pyaudio = pyaudio.PyAudio()
        self._stream = self.pyaudio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    output=True,
                    frames_per_buffer=self.frames_per_buffer
                    )

    def module_stop(self):
        self._stream.stop_stream()
        self._stream.close()
        self.pyaudio.terminate()


output_modules_class['pyaudio'] = PyAudioOutput
