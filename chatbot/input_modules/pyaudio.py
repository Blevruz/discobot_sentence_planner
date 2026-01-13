# chatbot/input_modules/pyaudio.py
from input_modules.dummy import DummyInput, input_modules_class
from utils.config import verbose
import pyaudio
import multiprocessing

class PyAudioInput(DummyInput):

    def action(self, i):
        raise NotImplementedError("PyAudioInput does not have an action module. It is a blocking module.")
        #data = self._stream.read(self.frames_per_buffer)
        #self.output_queue.put(data)

    def _fill_queue(self, in_data, *args, **kwargs):
        self.output_queue.put(in_data)
        status = pyaudio.paContinue if not self.stopped.is_set() else pyaudio.paComplete
        return (None, pyaudio.paContinue)


    def __init__(self, name="pyaudio_input", **args):
        DummyInput.__init__(self, name)
        self._loop_type = "blocking"  # We use a callback so it's fine to use blocking
        self._datatype_out = "audio"
        self.format = args.get('format', pyaudio.paInt16)
        self.channels = args.get('channels', 1)
        self.rate = args.get('rate', 16000)
        self.frames_per_buffer = args.get('frames_per_buffer', 4800)
        self.args = args
        self.pyaudio = pyaudio.PyAudio()
        self._stream = None


    def module_start(self):
        if verbose:
            print(f"[DEBUG] Starting PyAudioInput loop for {self.name}")
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
        if verbose:
            print(f"[DEBUG] Stopping PyAudioInput loop for {self.name}")
        self._stream.stop_stream()
        self._stream.close()
        self.pyaudio.terminate()



input_modules_class['pyaudio'] = PyAudioInput
