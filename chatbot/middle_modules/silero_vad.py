# chatbot/middle_modules/silero_vad.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import numpy as np
import torch
import time

class SileroVAD(DummyMiddle):
    """Voice Activity Detection using Silero VAD.

    Sits between a raw PCM audio source (e.g. PyAudioInput) and a
    transcriber (e.g. FasterWhisper). Accumulates incoming int16 PCM
    byte chunks, detects speech boundaries, and flushes complete
    utterances downstream as float32 numpy arrays.

    Parameters
    ----------
    sample_rate : int
        Must match the upstream source. Default 16000.
    speech_pad_ms : int
        Audio kept before speech onset and after speech end (ms).
        Prevents clipping of utterance edges. Default 300.
    silence_threshold_ms : int
        How long silence must persist after speech before the utterance
        is flushed downstream. Default 700.
    vad_threshold : float
        Silero speech probability threshold (0.0–1.0). Default 0.5.
    idle_sleep_s : float
        Seconds to sleep when the input queue is empty, to avoid
        burning CPU in a busy-wait loop. Default 0.005.
    """

    def _pcm_to_float32(self, raw_bytes):
        """Convert int16 PCM bytes to a normalized float32 ndarray."""
        return np.frombuffer(raw_bytes, dtype=np.int16) \
                 .astype(np.float32) / 32768.0

    def _vad_prob(self, chunk_f32):
        """Return Silero speech probability for a single float32 chunk.
        Silero requires exactly self._chunk_samples samples."""
        tensor = torch.from_numpy(chunk_f32)
        with torch.no_grad():
            return self.model(tensor, self.sample_rate).item()

    def _flush_utterance(self):
        """Concatenate the audio buffer and send it downstream."""
        utterance = np.concatenate(self._audio_buffer)
        self._in_speech = False
        self._audio_buffer = []
        self._silence_chunks = 0
        self._pad_buffer = []

        duration = len(utterance) / self.sample_rate
            utils.config.debug_print(
                f"[{self.name}] Flushing utterance ({duration:.2f}s)"
            )

        if len(self._output_queues['audio']) > 0:
            self._output_queues['audio'].put(utterance)

    def action(self, i):
        try:
            raw = self.input_queue.get()

            # Queue is non-blocking; sleep briefly on empty to avoid
            # spinning and burning CPU
            if raw is None:
                time.sleep(self.idle_sleep_s)
                return

            # Silero requires exactly _chunk_samples samples per call.
            # Accumulate a resampling buffer to handle arbitrary upstream
            # chunk sizes (e.g. PyAudio's 4800-frame default).
            self._resample_buffer += raw
            bytes_needed = self._chunk_samples * 2  # int16 = 2 bytes/sample

            while len(self._resample_buffer) >= bytes_needed:
                chunk_bytes = self._resample_buffer[:bytes_needed]
                self._resample_buffer = self._resample_buffer[bytes_needed:]

                chunk = self._pcm_to_float32(chunk_bytes)
                prob = self._vad_prob(chunk)
                is_speech = prob >= self.vad_threshold

                if is_speech:
                    if not self._in_speech:
                        # Speech onset: prepend pre-roll pad, start buffer
                        self._in_speech = True
                        self._silence_chunks = 0
                        self._audio_buffer = list(self._pad_buffer) + [chunk]
                        self._pad_buffer = []
                        utils.config.debug_print(
                                f"[{self.name}] Speech onset detected"
                            )
                    else:
                        self._silence_chunks = 0
                        self._audio_buffer.append(chunk)
                else:
                    if self._in_speech:
                        self._audio_buffer.append(chunk)
                        self._silence_chunks += 1
                        if self._silence_chunks >= self._silence_chunks_needed:
                            self._flush_utterance()
                            utils.config.debug_print(
                                    f"[{self.name}] Speech ended"
                                )
                    else:
                        # Outside speech: maintain rolling pre-roll window
                        self._pad_buffer.append(chunk)
                        if len(self._pad_buffer) > self._pad_chunks:
                            self._pad_buffer.pop(0)

        except Exception as e:
            utils.config.debug_print(f"Error in SileroVAD: {e}")

    def __init__(self, name="silero_vad", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "audio"

        self.sample_rate = args.get('sample_rate', 16000)
        self.vad_threshold = args.get('vad_threshold', 0.5)
        self.speech_pad_ms = args.get('speech_pad_ms', 300)
        self.silence_threshold_ms = args.get('silence_threshold_ms', 700)
        self.idle_sleep_s = args.get('idle_sleep_s', 0.005)

        self.model_path = args.get('model_path', 'snakers4/silero-vad')
        self.model_name = args.get('model_name', 'silero_vad')

        # Silero VAD requires exactly 512 samples at 16kHz, 256 at 8kHz
        self._chunk_samples = 512 if self.sample_rate == 16000 else 256
        chunk_ms = (self._chunk_samples / self.sample_rate) * 1000

        self._pad_chunks = max(1, int(self.speech_pad_ms / chunk_ms))
        self._silence_chunks_needed = max(1, int(self.silence_threshold_ms / chunk_ms))

        # State
        self._in_speech = False
        self._audio_buffer = []     # accumulates chunks during speech
        self._pad_buffer = []       # rolling pre-roll window
        self._silence_chunks = 0    # consecutive silent chunks since speech
        self._resample_buffer = b'' # handles mismatched upstream chunk sizes

        # Replace the inherited generic 'output'/'default' slots with
        # typed 'audio' ones. DummyModule creates 'output' as datatype='any',
        # so we just add our named slot and remap 'default'.
        self._output_queues['audio'] = QueueSlot(self, 'output', datatype='audio')
        self._output_queues['default'] = self._output_queues['audio']

        utils.config.debug_print(f"[{self.name}] Loading {self.model_name} model from {self.model_path}")

        self.model, _ = torch.hub.load(
            repo_or_dir=self.model_path,
            model=self.model_name,
            force_reload=False,
            trust_repo=True
        )
        self.model.eval()

        utils.config.debug_print(
                f"[{self.name}] Silero VAD ready — "
                f"threshold={self.vad_threshold}, "
                f"silence={self.silence_threshold_ms}ms, "
                f"pad={self.speech_pad_ms}ms, "
                f"chunk={self._chunk_samples} samples"
            )


middle_modules_class['silero_vad'] = SileroVAD
