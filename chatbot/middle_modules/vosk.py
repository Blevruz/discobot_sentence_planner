# chatbot/middle_modules/vosk.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import queue
import json
import vosk

# Important to keep in mind working with VOSK:
# - The model expects a sampling freq of 16kHz and a mono format


class VoskTranscriber(DummyMiddle):
    def action(self, i):
        try:
            audio_data = self.input_queue.get()
            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                self.output_queue.put(result.get("text", ""))
        except queue.Empty:
            # Handle timeout
            pass
        except Exception as e:
            print(f"Error processing audio: {e}")

    def __init__(self, name="vosk_transcriber", **args):
        DummyMiddle.__init__(self, name)
        self.samplerate = args.get('samplerate', 16000)
        self.timeout = args.get('timeout', 1)
        self._loop_type = "thread"
        self._datatype_in = "audio"
        self._datatype_out = "string"

        # Initialize Vosk
        self.model = vosk.Model(model_path) if model_path else vosk.Model(lang="en-us")
        self.recognizer = vosk.KaldiRecognizer(self.model, samplerate)

middle_modules_class['vosk'] = lambda n: VoskTranscriber(n, model_path="models/vosk/en")
