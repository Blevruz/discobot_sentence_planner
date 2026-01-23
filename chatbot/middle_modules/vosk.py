# chatbot/middle_modules/vosk.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import queue
import json
import vosk
import utils.config

# Important to keep in mind working with VOSK:
# - The model expects a sampling freq of 16kHz and a mono format

# TODO: output in-progress transcription, output confidence


class VoskTranscriber(DummyMiddle):
    """Uses Vosk to transcribe audio to text.
    
    """

    def action(self, i):
        try:
            audio_data = self.input_queue.get()
            if self.recognizer.AcceptWaveform(audio_data):
                result = json.loads(self.recognizer.Result())
                if utils.config.verbose:
                    if result.get('result'):
                        for word in result['result']:
                            if 'conf' in word:
                                utils.config.debug_print(f"word {word} confidence is: {word['conf']}")

                self.output_queue.put(result.get("text", ""))
        except queue.Empty:
            # Handle timeout
            pass
        except Exception as e:
            print(f"Error processing audio: {e}")

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
        self.timeout = args.get('timeout', 1)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "string"
        self.model_path = args.get('model_path', "models/vosk/en")

        # Initialize Vosk
        self.model = vosk.Model(self.model_path) if self.model_path else vosk.Model(lang="en-us")
        self.recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        self.recognizer.SetWords(True)

middle_modules_class['vosk'] = VoskTranscriber
