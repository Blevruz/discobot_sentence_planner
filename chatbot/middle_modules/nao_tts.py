# chatbot/middle_modules/nao_tts.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.nao
import utils.config
from utils.queues import QueueWrapper, QueueSlot
import qi

class NaoTTS(DummyMiddle):
    """Uses the NAO TTS engine to output the input.
    Queues:
        input: string
            Text to output
        output: signal (int)
            1 if currently speaking, 0 otherwise
    """

    def action(self, i):

        if len(self._input_queues['parameters']) > 0:
            params = self._input_queues['parameters'][0].get()
            if params:
                self.voice = params.get("voice", self.voice)
                self.session.service("ALTextToSpeech").setVoice(self.voice)
                self.language = params.get("language", self.language)
                self.session.service("ALTextToSpeech").setLanguage(self.language)

        speech = self.input_queue.get()
        if speech:
            self.output_queue.put(1)
            self.session.service("ALTextToSpeech").say(speech)
            self.output_queue.put(0)
        return


    def __init__(self, name = "nao_tts", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'
        self.datatype_out = 'int'
        self.session = qi.Session()
        # Takes in parameters
        self._input_queues["parameters"] = QueueSlot(self, "input", datatype='dict')
        self.ip = args.get("ip", "127.0.0.1")
        self.port = args.get("port", 9559)
        self.session = utils.nao.connect(self.ip, self.port)
        self.language = args.get("language", "English")
        self.voice = args.get("voice", "Judy")

    def module_start(self):
        self.session.service("ALTextToSpeech").setLanguage(self.language)

        #if utils.config.verbose:
        #    utils.config.debug_print(f"Initialized NAO TTS module {name} with ip {self.ip} and port {self.port}")

    def module_stop(self):
        if utils.config.verbose:
            utils.config.debug_print(f"Stopping NAO TTS module {self.name} with ip {self.ip} and port {self.port}")
        utils.nao.disconnect(self.ip, self.port)

middle_modules_class['nao_tts'] = NaoTTS


