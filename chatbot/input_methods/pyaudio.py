# chatbot/input_methods/pyaudio.py
from input_methods.dummy import DummyInput, input_methods_class
from utils.config import verbose
import pyaudio
import multiprocessing

class PyAudioInput(DummyInput):

    def action(self, i):
        raise NotImplementedError("PyAudioInput does not have an action method. It is a blocking module.")
        #data = self._stream.read(self.frames_per_buffer)
        #self.output_queue.put(data)

    def _fill_queue(self, in_data, *args, **kwargs):
        self.output_queue.put(in_data)
        status = pyaudio.paContinue if not self.stopped.is_set() else pyaudio.paComplete
        return (None, pyaudio.paContinue)


    
    def __init__(self, name="pyaudio_input", delay=0.0, timeout=1.0, **stream_args):
        DummyInput.__init__(self, name)
        self.loop_type = "blocking"  # We use a callback so it's fine to use blocking
        self.datatype_out = "audio"
        self.format = stream_args.get('format', pyaudio.paInt16)
        self.channels = stream_args.get('channels', 1)
        self.rate = stream_args.get('rate', 48000)
        self.frames_per_buffer = stream_args.get('frames_per_buffer', 48000)
        self.stream_args = stream_args
        self._stream_running = multiprocessing.Event()
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


            


input_methods_class['pyaudio'] = PyAudioInput
