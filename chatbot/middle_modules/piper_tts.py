# chatbot/middle_modules/piper_tts.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import piper
import wave
import utils.config
from utils.queues import QueueWrapper, QueueSlot

class PiperTTS(DummyMiddle):
    """Uses Piper to output text to speech.
    Outputs audio in 16-bit int format.
    NOTE!! sample rate is 22050 by default, and seemingly cannot
    be changed on generation. Adjust output module to match.
    """
    def __init__(self, name="piper_tts", **args):
        """Arguments:
            model : str
                Path to the model to use. See Piper documentation.
            volume : float
                Volume of the speech, 1 is the default.
            speed : float
                Speed of the speech, 1 is the default.
            noise_scale : float
                Induces audio variation, 0 is the default.
            noise_w_scale : float
                Induces speaking variation, 0 is the default.
            normalize_audio : bool
                Normalize the audio, True is the default.
        """
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'

        self._input_queues["parameters"] = QueueSlot(self, "input", datatype='dict')

        self.model = None
        self.speed = None
        self.volume = None
        self.noise_scale = None
        self.noise_w_scale = None
        self.normalize_audio = None
        self.synthesis_config = None

        self.parse_params(args)

        self.voice = piper.PiperVoice.load(self.model)

    def parse_params(self, params):
        self.model = params.get('model', "./models/piper/en_US-lessac-medium.onnx" if self.model == None else self.model)
        self.speed = params.get('speed', 1.0 if self.speed == None else self.speed)
        if self.speed == 0:
            self.speed = 1

        self.synthesis_config = piper.SynthesisConfig(
                            volume = params.get('volume', 1.0 if self.volume == None else self.volume),
                            length_scale = 1/self.speed,
                            noise_scale = params.get('noise_scale', 1.0 if self.noise_scale == None else self.noise_scale),
                            noise_w_scale = params.get('noise_w_scale', 1.0 if self.noise_w_scale == None else self.noise_w_scale),
                            normalize_audio = params.get('normalize_audio', True if self.normalize_audio == None else self.normalize_audio),
                            )

    def action(self, i):
        if len(self._input_queues['parameters']) > 0:
            params = self._input_queues['parameters'].get()
            if params:
                self.parse_params(params)
        text = self.input_queue.get()
        if text is not None:
            for chunk in self.voice.synthesize(text, syn_config=self.synthesis_config):
                #wave.set_audio_format(chunk.sample_rate, chunk.sample_width, chunk.sample_channels)
                self.output_queue.put(chunk.audio_int16_bytes)


middle_modules_class['piper_tts'] = PiperTTS
