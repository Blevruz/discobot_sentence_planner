# chatbot/middle_modules/espeak-ng.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.config
import subprocess

class EspeakNG(DummyMiddle):
    """Uses espeak-ng to middle text to speech.
    Queues:
        input: string
            Text to output
        output: signal (int)
            1 if currently outputting, 0 otherwise
    """
    def __init__(self, name="espeakng", **args):
        """Arguments:
            voice : str
                Voice to use. See espeak-ng documentation.
            speed : int
                Speed of the speech. See espeak-ng documentation.
        """
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.datatype_out = 'int'
        self.voice = args.get('voice', 'en')
        self.speed = args.get('speed', 150)

    def action(self, i):
        if not self.input_queue.empty():
            text = self.input_queue.get()
            command = f"espeak-ng -v {self.voice} -s {self.speed} \"{text}\""
            self.output_queue.put(1)
            subprocess.call(command, shell=True)
            self.output_queue.put(0)


middle_modules_class['espeak-ng'] = EspeakNG

