# chatbot/input_methods/sounddevice.py
from input_methods.dummy import DummyInput, input_methods_class
import sounddevice as sd
import numpy as np
import multiprocessing
import time

class SoundDeviceInput(DummyInput):
    def __init__(self, name="sound_input", delay=0.0, timeout=1.0, **stream_args):
        DummyInput.__init__(self, name)
        self.loop_type = "process"  # Use multiprocessing
        self.stream_args = stream_args
        self._stream_running = multiprocessing.Event()
        self._process = None

    def _loop(self):
        """Runs in a separate process to manage the audio stream."""
        self._stream_running.set()
        try:
            with sd.RawInputStream(callback=self._audio_callback, **self.stream_args) as stream:
                self._stream = stream
                # Keep process alive while running
                while self._stream_running.is_set():
                    time.sleep(0.1)
        finally:
            self._stream_running.clear()

    def _audio_callback(self, indata, frames, time, status):
        """Audio callback: processes frames and puts them in the queue."""
        if status:
            print(f"Audio stream status: {status}")
        audio_data = np.frombuffer(indata, dtype=self.stream_args.get('dtype', 'float32'))
        self.output_queue.put(audio_data)

    def start_loop(self, verbose=False):
        """Starts the audio stream in a new process."""
        self._process = multiprocessing.Process(target=self._loop)
        self._process.start()

    def stop_loop(self, verbose=False):
        """Stops the audio stream and process."""
        self._stream_running.clear()
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join()

input_methods_class = dict()
input_methods_class['sounddevice'] = SoundDeviceInput

