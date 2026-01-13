# chatbot/input_modules/wav.py
from input_modules.dummy import DummyInput, input_modules_class
import utils.config
import wave

class WavInput(DummyInput):

    def action(self, i):
        if len(data := self.wf.readframes(self.frames_per_buffer)):
            self.output_queue.put(data)

    def __init__(self, name="wav_input", **args):
        DummyInput.__init__(self, name)
        self.frames_per_buffer = args.get('frames_per_buffer', 48000)
        self._loop_type = "thread"  # Use threading
        self.datatype_out = "audio"
        self.file_path = args.get('file_path', "fitnessgram.wav")
        self.wf = None

    def module_start(self):
        if utils.config.verbose:
            print(f"[DEBUG] Starting WavInput loop for {self.name}")
        self.wf = wave.open(f"{self.file_path}", 'rb')

    def module_stop(self):
        if utils.config.verbose:
            print(f"[DEBUG] Stopping WavInput loop for {self.name}")
        self.wf.close()

input_modules_class['wav'] = WavInput

