# chatbot/output_methods/pyaudio.py
from output_methods.dummy import DummyOutput, output_methods_class
from utils.config import verbose
import pyaudio

class PyAudioOutput(DummyOutput):

    def action(self, i):
        self._stream.write(self.input_queue.get())

    def __init__(self, name="pyaudio_output", delay=0.0, timeout=1.0, **stream_args):
        DummyOutput.__init__(self, name)
        self.loop_type = "process"
        self.datatype_in = "audio"
        self.datatype_out = "audio"
        self.format = stream_args.get('format', pyaudio.paInt16)
        self.channels = stream_args.get('channels', 1)
        self.rate = stream_args.get('rate', 48000)
        self.frames_per_buffer = stream_args.get('frames_per_buffer', 48000)
        self.stream_args = stream_args
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


output_methods_class['pyaudio'] = PyAudioOutput
