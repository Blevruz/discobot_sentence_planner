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

    def update_params(self, params):
        for key, value in params.items(): 
            utils.config.debug_print(f"[{self.name}] Setting parameter {key} to {value}")
            if key == "voice":
                self.voice = value
                self.session.service("ALTextToSpeech").setVoice(self.voice)
            elif key == "language":
                self.language = value
                self.session.service("ALTextToSpeech").setLanguage(self.language)
            elif key == "volume":
                self.volume = value
                self.session.service("ALTextToSpeech").setVolume(self.volume)
            else:
                self.session.service("ALTextToSpeech").setParameter(key, value)

    def action(self, i):

        if len(self._input_queues['parameters']) > 0:
            params = self._input_queues['parameters'].get()
            if params:
                #self.voice = params.get("voice", self.voice)
                #self.session.service("ALTextToSpeech").setVoice(self.voice)
                self.update_params(params)

        speech = self.input_queue.get()
        if speech:
            self.output_queue.put(1)
            utils.config.debug_print(f"[{self.name}] Speaking: {speech}")
            self.session.service("ALTextToSpeech").say(speech)
            utils.config.debug_print(f"[{self.name}] Finished speaking")
            self.output_queue.put(2)
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
        self.session = None
        self.language = args.get("language", "English")
        self.voice = args.get("voice", "Judy")

    def module_start(self):
        self.session = utils.nao.connect(self.ip, self.port)

        params = {
            "language": self.language,
            "volume": 1.0,
            "speed": 125,
            }
        self.update_params(params)


        utils.config.debug_print(f"[{self.name}] Initialized NAO TTS module {self.name} with ip {self.ip} and port {self.port}")

    def module_stop(self):
        utils.config.debug_print(f"[{self.name}] Stopping NAO TTS module {self.name} with ip {self.ip} and port {self.port}")
        utils.nao.disconnect(self.ip, self.port)

middle_modules_class['nao_tts'] = NaoTTS


