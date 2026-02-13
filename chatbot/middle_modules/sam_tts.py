# chatbot/output_modules/sam_tts.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import subprocess
import os
import utils.config

class SamTTS(DummyMiddle):
    """Uses SAM (Software Automatic Mouth) to output text to speech.
    Queues:
        input: string
            Text to output
        output: signal (int)
            1 if SAM is currently outputting, 0 otherwise
    """
    def __init__(self, name="sam_tts", **args):
        """Arguments:
            path_to_sam : str
                Path to the SAM executable
        """
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.datatype_out = 'int'
        self.path_to_sam = args.get('path_to_sam', "./misc")

    def action(self, i):
        text = self.input_queue.get()
        if text:
            for t in text.split(" "):
                self.output_queue.put(1)
                subprocess.run([f"{self.path_to_sam}/sam", f"{t}." ])
                self.output_queue.put(0)


middle_modules_class['sam_tts'] = SamTTS
