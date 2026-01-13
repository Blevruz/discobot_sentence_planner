# chatbot/input_methods/wav.py
from input_methods.dummy import DummyInput, input_methods_class
from utils.config import verbose
import wave

class WavInput(DummyInput):

    def action(self, i):
        if len(data := self.wf.readframes(self.frames_per_buffer)):
            self.output_queue.put(data)

    def __init__(self, name="wav_input", wav_file_path="fitnessgram.wav", **args):
        DummyInput.__init__(self, name)
        self.frames_per_buffer = args.get('frames_per_buffer', 48000)
        self.loop_type = "thread"  # Use threading
        self.datatype_out = "audio"
        self.file_path = wav_file_path
        self.wf = None

    def module_start(self):
        if verbose:
            print(f"[DEBUG] Starting WavInput loop for {self.name}")
        self.wf = wave.open(f"{self.file_path}", 'rb')

    def module_stop(self):
        if verbose:
            print(f"[DEBUG] Stopping WavInput loop for {self.name}")
        self.wf.close()

input_methods_class['wav'] = WavInput

