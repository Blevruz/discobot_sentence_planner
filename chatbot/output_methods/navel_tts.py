# chatbot/output_methods/navel_tts.py
from output_methods.dummy import DummyOutput, output_methods_class

import navel

class NavelTTS(DummyOutput):

    def action(self, i):
        while not self.input_queue.empty():
            navel.run(lambda r: r.say(self.input_queue.get()))
        return


    def __init__(self, name = "navel_tts", **args):
        DummyOutput.__init__(self, name)
        self.loop_type = 'thread'
        self.datatype_in = 'string'

output_methods_class['navel_tts'] = NavelTTS
