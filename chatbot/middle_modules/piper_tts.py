# chatbot/middle_modules/piper_tts.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import piper

class PiperTTS(DummyMiddle):
    """Uses Piper to output text to speech.
    """
    def __init__(self, name="piper_tts", **args):
        """Arguments:
            model : str
                Path to the model to use. See Piper documentation.
            speed : float
                Speed of the speech. See Piper documentation.
        """
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.model = args.get('model', "./models/piper/en_US-lessac-medium.onnx")
        self.speed = args.get('speed', 1.0)
        self.voice = piper.PiperVoice.load(self.model)

    def action(self, i):
        if not self.input_queue.empty():
            text = self.input_queue.get()
            for chunk in self.voice.synthesize(text, speed=self.speed):
                self.output_queue.put(chunk)


middle_modules_class['piper_tts'] = PiperTTS
