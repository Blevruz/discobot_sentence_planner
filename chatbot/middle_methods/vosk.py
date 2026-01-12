# chatbot/middle_methods/vosk.py
from middle_methods.dummy import DummyMiddle, middle_methods_class
import queue
import json
import vosk

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

    def __init__(self, name="vosk_transcriber", model_path=None, samplerate=16000, timeout=5.0, **stream_args):
        DummyMiddle.__init__(self, name)
        self.samplerate = samplerate
        self.timeout = timeout
        self.loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "string"

        # Initialize Vosk
        self.model = vosk.Model(model_path) if model_path else vosk.Model(lang="en-us")
        self.recognizer = vosk.KaldiRecognizer(self.model, samplerate)

middle_methods_class['vosk'] = lambda n: VoskTranscriber(n, model_path="models/vosk/en")
