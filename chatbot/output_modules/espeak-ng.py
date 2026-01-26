# chatbot/output_modules/espeak-ng.py
from output_modules.dummy import DummyOutput, output_modules_class
import utils.config
import subprocess

class EspeakNG(DummyOutput):
    """Uses espeak-ng to output text to speech.
    """
    def __init__(self, name="espeakng", **args):
        """Arguments:
            voice : str
                Voice to use. See espeak-ng documentation.
            speed : int
                Speed of the speech. See espeak-ng documentation.
        """
        DummyOutput.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.voice = args.get('voice', 'en')
        self.speed = args.get('speed', 150)

    def action(self, i):
        if not self.input_queue.empty():
            text = self.input_queue.get()
            command = f"espeak-ng -v {self.voice} -s {self.speed} \"{text}\""
            subprocess.call(command, shell=True)


output_modules_class['espeak-ng'] = EspeakNG

