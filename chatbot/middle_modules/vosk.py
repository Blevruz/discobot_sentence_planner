# chatbot/middle_modules/vosk.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import queue
import json
import vosk
import utils.config

# Important to keep in mind working with VOSK:
# - The model expects a sampling freq of 16kHz and a mono format


class VoskTranscriber(DummyMiddle):
    """Uses Vosk to transcribe audio to text.
    
    """

    def action(self, i):
        try:
            audio_data = self.input_queue.get()
    
            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
    
                words = result.get('result', [])
                text = result.get("text", "")
    
                # --- Compute confidence ---
                if words:
                    confs = [w.get("conf", 0.0) for w in words if "conf" in w]
                    avg_conf = sum(confs) / len(confs) if confs else 0.0
                else:
                    avg_conf = 0.0
    
                if utils.config.verbose:
                    utils.config.debug_print(f"[{self.name}][{self.name}] TEXT='{text}' CONF={avg_conf:.3f}")
    
                # --- Output streams ---
                self._output_queues['text'][0].put(text)
                self._output_queues['confidence'][0].put(avg_conf)

        except queue.Empty:
            pass
        except Exception as e:
            print(f"[{self.name}] Error processing audio: {e}")


    def __init__(self, name="vosk_transcriber", **args):
        """Arguments:
            model_path : str
                Path to the Vosk model to use
            samplerate : int
                Sampling rate of the audio
            timeout : int
                Timeout for the recognizer
        """

        DummyMiddle.__init__(self, name, **args)
        self.samplerate = args.get('samplerate', 16000)
        self.timeout = args.get('timeout', 100)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "string"
        self.model_path = args.get('model_path', "models/vosk/en")

        self._output_queues['text'] = QueueSlot(self, 'output', datatype='string')
        self._output_queues['confidence'] = QueueSlot(self, 'output', datatype='float')
        self._output_queues['default'] = self._output_queues['text']

        # Initialize Vosk
        self.model = vosk.Model(self.model_path) if self.model_path else vosk.Model(lang="en-us")
        self.recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        self.recognizer.SetWords(True)

middle_modules_class['vosk'] = VoskTranscriber
