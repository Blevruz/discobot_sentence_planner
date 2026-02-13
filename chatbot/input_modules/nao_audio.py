# chatbot/input_modules/nao_audio.py
from input_modules.dummy import DummyInput, input_modules_class
import utils.nao
import utils.config
import qi
import threading
import numpy as np
import time

# SO apparently you can't use ALAudioDevice with qi ????


class AudioCallbackHandler(qi.Object):
    def __init__(self, output_queue, owner):
        super().__init__()
        self.output_queue = output_queue
        self.owner = owner


    def processRemote(self, nbOfChannels, nbOfSamplesByChannel, timeStamp, inputBuffer):
        """
        This method is called by ALAudioDevice when new audio is available.
        Must be named exactly 'processRemote' for NAOqi to recognize it.
        """
        try:
            # Convert to bytes and put in queue
            audio_array = np.frombuffer(inputBuffer, dtype=np.int16)
            self.output_queue.put(audio_array.tobytes())
        except Exception as e:
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.owner.name}] Callback error: {e}")

class NaoAudioInput(DummyInput):
    """NAO microphone input module using ALAudioDevice."""

    def action(self, i):
        raise NotImplementedError("NaoAudioInput does not use action(); it runs in a background thread.")

    def __init__(self, name="nao_audio_input", **args):
        super().__init__(name, **args)

        self._loop_type = "blocking"
        self.datatype_out = "audio"

        self.ip = args.get("ip", "169.254.254.31")
        self.port = args.get("port", 9559)

        self.channels = args.get('channels', 1)
        self.rate = args.get('rate', 16000)
        self.frames_per_buffer = args.get('frames_per_buffer', 4800)

        self.session = None
        self.audio_device = None
        self.subscriber_name = f"NaoAudioSubscriber_{self.name}"

        self.callback_handler = None

    def _connect(self):
        self.session = utils.nao.connect(self.ip, self.port)

        self.audio_device = self.session.service("ALAudioDevice")

        self.callback_handler = AudioCallbackHandler(self.output_queue, self)

        self.session.listen("tcp://0.0.0.0:9558")

        self.session.registerService(self.subscriber_name, self.callback_handler)

        self.audio_device.setClientPreferences(self.subscriber_name, self.rate, self.channels, 0)

        self.audio_device.subscribe(self.subscriber_name)


        if utils.config.verbose:
            utils.config.debug_print(f"[{self.name}]Connected to NAO at {self.ip}:{self.port}")

    def _disconnect(self):
        try:
            if self.audio_device is not None:
                try:
                    self.audio_device.unsubscribe(self.subscriber_name)
                except:
                    pass

            if self.session is not None:
                utils.nao.disconnect(self.ip, self.port)

            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}]Disconnected from NAO at {self.ip}:{self.port}")
        except Exception as e:
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}]Error in disconnect: {e}")



    def module_start(self):
        self._connect()
        

    def module_stop(self):
        self._disconnect()


input_modules_class['nao_audio'] = NaoAudioInput

