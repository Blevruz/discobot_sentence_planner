# chatbot/input_modules/pyaudio.py
from input_modules.dummy import DummyInput, input_modules_class
import utils.config
import pyaudio
import multiprocessing

class PyAudioInput(DummyInput):
    """PyAudio input module. Takes audio input from the microphone."""

    def action(self, i):
        """Disabled, the entire audio output process is handled by a callback."""
        raise NotImplementedError("PyAudioInput does not have an action module. It is a blocking module.")
        #data = self._stream.read(self.frames_per_buffer)
        #self.output_queue.put(data)

    def _fill_queue(self, in_data, *args, **kwargs):
        """Fill the output queue with audio data."""
        self.output_queue.put(in_data)
        status = pyaudio.paContinue if not self.stopped.is_set() else pyaudio.paComplete
        return (None, pyaudio.paContinue)


    def __init__(self, name="pyaudio_input", **args):
        """
        Initializes pyaudio, doesn't open the stream.
        Arguments:
            format : pyaudio format (default: pyaudio.paInt16)
                TODO handle input as a json-friendly type
                Type of sample data. See pyaudio documentation.
            channels : int (default: 1)
                number of channels in the stream
            rate : int (default: 16000)
                sample rate 
            frames_per_buffer : int 
                number of frames per buffer (default: 4800)
        """
        DummyInput.__init__(self, name, **args)
        self._loop_type = "blocking"  # We use a callback so it's fine to use blocking
        self.datatype_out = "audio"
        self.format = args.get('format', pyaudio.paInt16)
        self.channels = args.get('channels', 1)
        self.rate = args.get('rate', 16000)
        self.frames_per_buffer = args.get('frames_per_buffer', 4800)
        self.args = args
        self.pyaudio = pyaudio.PyAudio()
        self._stream = None


    def module_start(self):
        """
        Starts the pyaudio stream. Callback replaces the usual loop.
        """

        if utils.config.verbose:
            utils.config.debug_print(f"Starting PyAudioInput loop for {self.name}")
            utils.config.debug_print(f"PyAudioInput loop for {self.name}: {self.format}, {self.channels}, {self.rate}, {self.frames_per_buffer}")
        self._stream = self.pyaudio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.frames_per_buffer,
                    # fill queue thru callback
                    stream_callback=self._fill_queue
                )

    def module_stop(self):
        """
        Stops the pyaudio stream.
        """
        if utils.config.verbose:
            utils.config.debug_print(f"Stopping PyAudioInput loop for {self.name}")
        self._stream.stop_stream()
        self._stream.close()
        self.pyaudio.terminate()



input_modules_class['pyaudio'] = PyAudioInput
