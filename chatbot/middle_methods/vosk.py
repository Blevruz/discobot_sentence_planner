# chatbot/middle_methods/vosk.py
from input_methods.dummy import DummyModule
import sounddevice as sd
import queue
import json
import vosk
import threading
import time
import numpy as np

class VoskTranscriber(DummyModule):
    def __init__(self, name="vosk_transcriber", model_path=None, samplerate=16000, timeout=5.0, **stream_args):
        DummyModule.__init__(self, name)
        self.samplerate = samplerate
        self.timeout = timeout
        self.loop_type = "thread"
        self._input_queues = []
        self._output_queues = []
        self._audio_queue = queue.Queue()
        self._stream = None
        self._stopped = threading.Event()

        # Initialize Vosk
        self.model = vosk.Model(model_path) if model_path else vosk.Model(lang="en-us")
        self.recognizer = vosk.KaldiRecognizer(self.model, samplerate)
        
        # Stream parameters
        self.stream_args = {
            'samplerate': samplerate,
            'dtype': 'int16',
            'channels': 1,
            'callback': self._audio_callback,
            **stream_args
        }

    def _loop(self):
        """Processes audio from queue and performs speech recognition."""
        self._stopped.clear()
        
        with sd.RawInputStream(**self.stream_args) as stream:
            self._stream = stream
            print("🎤 Listening...")
            
            while not self._stopped.is_set():
                try:
                    audio_data = self._audio_queue.get(timeout=self.timeout)
                    if self.recognizer.AcceptWaveform(audio_data):
                        result = json.loads(self.recognizer.Result())
                        self.output_queue.put(result.get("text", ""))
                except queue.Empty:
                    # Handle timeout
                    pass
                except Exception as e:
                    print(f"Error processing audio: {e}")

    def _audio_callback(self, indata, frames, time, status):
        """Audio callback: converts and puts audio data into processing queue."""
        if status:
            print(f"Audio stream status: {status}")
        
        # Convert CFFI buffer to bytes
        audio_bytes = bytes(indata)
        self._audio_queue.put(audio_bytes)

    def start_loop(self):
        """Starts audio capture and processing thread."""
        self.loop = threading.Thread(target=self._loop)
        self.loop.start()

    def stop_loop(self):
        """Stops audio capture and processing."""
        self._stopped.set()
        if self._stream:
            self._stream.abort()
        if hasattr(self, 'loop'):
            self.loop.join(timeout=2.0)

middle_methods_class = dict()
middle_methods_class['vosk'] = VoskTranscriber

