# chatbot/input_modules/wav.py
from input_modules.dummy import DummyInput, input_modules_class
import utils.config
import wave

class WavInput(DummyInput):
    """Audio input from a wav file"""

    def action(self, i):
        """Reads frames from the wav file and puts them in the output queue"""
        if len(data := self.wf.readframes(self.frames_per_buffer)):
            self.output_queue.put(data)

    def __init__(self, name="wav_input", **args):
        """Initializes the module.
        Arguments:
            file_path : str
                Path to the wav file to read
            frames_per_buffer : int
                Number of frames to read at a time
            rate : int
                Sample rate to use for the input
        """
        DummyInput.__init__(self, name, **args)
        self.frames_per_buffer = args.get('frames_per_buffer', 48000)
        self.rate = args.get('rate', 16000)
        self._loop_type = "thread"  # Use threading
        self.datatype_out = "audio"
        self.file_path = args.get('file_path', "fitnessgram.wav")
        self.wf = None

    def module_start(self):
        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Starting WavInput loop for {self.name}")
        self.wf = wave.open(f"{self.file_path}", 'rb')
        self.ratio = self.wf.getframerate()/self.rate
        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Loaded file \"{self.file_path}\" with " \
                    f"{self.wf.getnchannels()} channels, " \
                    f"{self.wf.getsampwidth()} sample width, " \
                    f"{self.wf.getnframes()} audio frames, " \
                    f"{self.wf.getcompname()} compression, " \
                    f"{self.wf.getframerate()} frames per second.")


    def module_stop(self):
        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Stopping WavInput loop for {self.name}")
        self.wf.close()

input_modules_class['wav'] = WavInput

