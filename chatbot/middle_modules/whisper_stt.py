# chatbot/middle_modules/whisper_stt.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot

class WhisperSTT(DummyMiddle):
    """Uses Whisper to transcribe audio to text.
    
    """

    def action(self, i):
        try:
            audio_data = self.input_queue.get()

    def __init__(self, name="whisper_stt", **args):
        """Initializes the module.
        Arguments:
            model : str
                Path to the Whisper model to use
            url : str
                URL of the Whisper API
            api : str
                API endpoint of the Whisper API, appended to URL during requests
        """




