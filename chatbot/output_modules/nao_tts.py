# chatbot/output_modules/nao_tts.py
from output_modules.dummy import DummyOutput, output_modules_class
import utils.nao
import utils.config
from utils.queues import QueueWrapper, QueueSlot
import qi

class NaoTTS(DummyOutput):
    """Uses the NAO TTS engine to output the input.
    """

    def action(self, i):

        if len(self._input_queues['parameters']) > 0:
            params = self._input_queues['parameters'][0].get()
            if params:
                self.language = params.get("language", self.language)
                self.session.service("ALTextToSpeech").setLanguage(self.language)

        speech = self.input_queue.get()
        if speech:
            self.session.service("ALTextToSpeech").say(speech)
        return


    def __init__(self, name = "nao_tts", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'
        self.session = qi.Session()
        # Takes in parameters
        self._input_queues["parameters"] = QueueSlot(self, "input", datatype='dict')
        self.ip = args.get("ip", "127.0.0.1")
        self.port = args.get("port", 9559)
        self.session = utils.nao.connect(self.ip, self.port)
        self.language = args.get("language", "English")
        self.session.service("ALTextToSpeech").setLanguage(self.language)
    

output_modules_class['nao_tts'] = NaoTTS


