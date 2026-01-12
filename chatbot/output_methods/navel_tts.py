# chatbot/output_methods/navel_tts.py
from output_methods.dummy import DummyOutput

import navel

class NavelTTS(DummyOutput):

    def action(self, i):
        while not self.input_queue.empty():
            navel.run(lambda r: r.say(self.input_queue.get()))
        return


    def __init__(self, name = "navel_tts", verbose=False):
        DummyOutput.__init__(self, name, verbose)
        self.loop_type = 'thread'

output_methods_class['navel_tts'] = NavelTTS
