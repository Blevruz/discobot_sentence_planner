# chatbot/output_modules/pyaudio.py
from output_modules.dummy import DummyOutput, output_modules_class
import utils.config
import pyaudio

class PyAudioOutput(DummyOutput):

    def action(self, i):
        self._stream.write(self.input_queue.get())

    def __init__(self, name="pyaudio_output", **args):
        DummyOutput.__init__(self, name, **args)
        self._loop_type = "process"
        self.datatype_in = "audio"
        self.datatype_out = "audio"
        self.format = args.get('format', pyaudio.paInt16)
        self.channels = args.get('channels', 1)
        self.rate = args.get('rate', 16000)
        self.frames_per_buffer = args.get('frames_per_buffer', 48000)
        self.args = args
        self.pyaudio = None
        self._stream = None

    def module_start(self):
        if utils.config.verbose:
            print(f"[DEBUG] Starting PyAudioInput loop for {self.name}")
            print(f"[DEBUG] PyAudioInput loop for {self.name}: {self.format}, {self.channels}, {self.rate}, {self.frames_per_buffer}")
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
