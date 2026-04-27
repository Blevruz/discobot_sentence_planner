# chatbot/output_modules/navel_tts.py
from output_modules.dummy import DummyOutput, output_modules_class

import navel

class NavelTTS(DummyOutput):
    """Uses the Navel TTS engine to output the input.
    Queues:
        input: string
            Text to output
        output: signal (int)
            1 if currently speaking, 0 otherwise
    """

    def action(self, i):

        if len(self._input_queues['parameters']) > 0:
            params = self._input_queues['parameters'].get()
            if params:
                self.update_parameters(params)

        speech = self.input_queue.get()
        if speech:
            self.output_queue.put(1)
            utils.config.debug_print(f"[{self.name}] Speaking: {speech}")
            utils.config.debug_print(f"[{self.name}] Finished speaking")
            self.output_queue.put(2)
        return


    def __init__(self, name = "navel_tts", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'

        self._input_queues["parameters"] = QueueSlot(self, "input", datatype='dict')
        self.language = args.get("language", "en1")
        self.volume = args.get("volume", 1.0)
        self.pitch = args.get("pitch", 1.0)
        self.speed = args.get("speed", 1.0)
        self.update_parameters(params = None)

    def say(self, text):
        navel.run(lambda r: r.say(speech))

    def update_parameters(self, params = None):
        if params:
            self.language = params.get("language", self.language)
            self.volume = params.get("volume", self.volume)
            self.pitch = params.get("pitch", self.pitch)
            self.speed = params.get("speed", self.speed)
        self.say(f"<lang,{self.language}><vol,{self.volume}><rpit,{self.pitch}><rspd,{self.speed}>")



output_modules_class['navel_tts'] = NavelTTS
