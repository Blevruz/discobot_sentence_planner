# chatbot/output_modules/sam_tts.py
from output_modules.dummy import DummyOutput, output_modules_class
import subprocess
import os
import utils.config

class SamTTS(DummyOutput):
    def __init__(self, name="sam_tts", **args):
        DummyOutput.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.path_to_sam = args.get('path_to_sam', "./misc/sam")

    def action(self, i):
        if not self.input_queue.empty():
            text = self.input_queue.get()
            for t in text.split(" "):
                subprocess.run([f"{self.path_to_sam}/sam", t ])


output_modules_class['sam_tts'] = SamTTS
