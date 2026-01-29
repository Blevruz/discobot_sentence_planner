# chatbot/output_modules/navel_tts.py
from output_modules.dummy import DummyOutput, output_modules_class

import navel

class NavelTTS(DummyOutput):
    """Uses the Navel TTS engine to output the input.
    """

    def action(self, i):
        speech = self.input_queue.get()
        if speech:
            navel.run(lambda r: r.say(speech))
        return


    def __init__(self, name = "navel_tts", **args):
        DummyOutput.__init__(self, name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'

output_modules_class['navel_tts'] = NavelTTS
