# chatbot/output_modules/pyaudio.py
from output_modules.dummy import DummyOutput, output_modules_class
import utils.config
import pyaudio

class PyAudioOutput(DummyOutput):
    """Uses PyAudio to output audio.
    """

    def action(self, i):
        self._stream.write(self.input_queue.get())

    def __init__(self, name="pyaudio_output", **args):
        """Arguments:
            format : pyaudio types (default pyaudio.paInt16)
                Format of the audio
            channels : int
                Number of channels of the audio
            rate : int
                Sampling rate of the audio
            frames_per_buffer : int
                Number of frames per buffer
        """
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
            utils.config.debug_print(f"Starting PyAudioInput loop for {self.name}")
            utils.config.debug_print(f"PyAudioInput loop for {self.name}: {self.format}, {self.channels}, {self.rate}, {self.frames_per_buffer}")
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
