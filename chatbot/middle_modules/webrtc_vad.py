# chatbot/middle_modules/webrtc_vad.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import collections
import webrtcvad
import numpy as np
import time

class WebRTCVAD(DummyMiddle):
    """Voice Activity Detection using py-webrtcvad.

    Sits between a raw PCM audio source (e.g. PyAudioInput) and a
    transcriber (e.g. FasterWhisper). Accumulates incoming int16 PCM
    byte chunks, uses a sliding ring buffer to detect speech onset and
    end, then flushes complete utterances downstream as float32 arrays.

    Uses the same triggered/untriggered sliding window algorithm as the
    py-webrtcvad example: speech is triggered when >90% of the ring
    buffer frames are voiced, and ends when >90% are unvoiced.

    Parameters
    ----------
    sample_rate : int
        Must match the upstream source. Must be 8000, 16000, 32000, or
        48000. Default 16000.
    aggressiveness : int
        webrtcvad aggressiveness mode, 0–3. Higher values are more
        aggressive about filtering non-speech. Default 2.
    frame_duration_ms : int
        Duration of each VAD frame in milliseconds. Must be 10, 20, or
        30. Default 30.
    padding_duration_ms : int
        Size of the sliding ring buffer in milliseconds. Controls how
        much audio context is used to make triggered/untriggered
        decisions, and how much pre-roll is preserved at speech onset.
        Default 300.
    speech_trigger_ratio : float
        Fraction of ring buffer frames that must be voiced to trigger
        speech onset. Default 0.9.
    silence_trigger_ratio : float
        Fraction of ring buffer frames that must be unvoiced to trigger
        speech end. Default 0.9.
    silence_timeout_s : float
        Seconds of silence before the utterance is flushed downstream.
    idle_sleep_s : float
        Seconds to sleep when the input queue is empty. Default 0.005.
    """

    def _flush_utterance(self, voiced_frames):
        """Convert accumulated PCM byte frames to float32 and flush."""
        raw = b''.join(f for f in voiced_frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        duration = len(audio) / self.sample_rate
        utils.config.debug_print(
                f"[{self.name}] Flushing utterance ({duration:.2f}s, "
                f"{len(voiced_frames)} frames)"
            )

        if len(self._output_queues['audio']) > 0:
            self._output_queues['audio'][0].put(audio)

    def action(self, i):
        try:
            raw = self.input_queue.get()

            if raw is None:
                time.sleep(self.idle_sleep_s)
                return

            self._resample_buffer += raw

            while len(self._resample_buffer) >= self._frame_bytes:
                frame_bytes = self._resample_buffer[:self._frame_bytes]
                self._resample_buffer = self._resample_buffer[self._frame_bytes:]

                is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

                if not self._triggered:
                    self._ring_buffer.append((frame_bytes, is_speech))
                    num_voiced = sum(1 for _, s in self._ring_buffer if s)

                    if num_voiced > self.speech_trigger_ratio * self._ring_buffer.maxlen:
                        self._triggered = True
                        # Flush ring buffer into voiced_frames to preserve
                        # the pre-roll audio that led to the trigger
                        for f, _ in self._ring_buffer:
                            self._voiced_frames.append(f)
                        self._ring_buffer.clear()
                        utils.config.debug_print(
                                f"[{self.name}] Speech onset detected"
                            )
                else:
                    self._voiced_frames.append(frame_bytes)
                    self._ring_buffer.append((frame_bytes, is_speech))
                    num_unvoiced = sum(1 for _, s in self._ring_buffer if not s)

                    if num_unvoiced > self.silence_trigger_ratio * self._ring_buffer.maxlen:
                        self.silence_duration += self.frame_duration_ms / 1000.0
                        if self.silence_duration > self.silence_timeout_s:
                            self.silence_duration = 0
                            self._triggered = False
                            self._flush_utterance(self._voiced_frames)
                            self._voiced_frames = []
                            self._ring_buffer.clear()
                            utils.config.debug_print(
                                    f"[{self.name}] Speech ended"
                                )
                    else:
                        self.silence_duration = 0

        except Exception as e:
            utils.config.debug_print(f"Error in WebRTCVAD: {e}")

    def __init__(self, name="webrtcvad_vad", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "audio"

        self.sample_rate = args.get('sample_rate', 16000)
        self.aggressiveness = args.get('aggressiveness', 1)
        self.frame_duration_ms = args.get('frame_duration_ms', 30)
        self.padding_duration_ms = args.get('padding_duration_ms', 300)
        self.speech_trigger_ratio = args.get('speech_trigger_ratio', 0.9)
        self.silence_trigger_ratio = args.get('silence_trigger_ratio', 0.9)
        self.silence_timeout_s = args.get('silence_timeout_s', 0.3)
        self.idle_sleep_s = args.get('idle_sleep_s', 0.005)

        assert self.sample_rate in (8000, 16000, 32000, 48000), \
            f"sample_rate must be 8000, 16000, 32000, or 48000, not {self.sample_rate}"
        assert self.frame_duration_ms in (10, 20, 30), \
            f"frame_duration_ms must be 10, 20, or 30, not {self.frame_duration_ms}"

        # Number of bytes per VAD frame: sample_rate * duration * 2 bytes/sample
        self._frame_bytes = int(self.sample_rate * (self.frame_duration_ms / 1000.0) * 2)
        num_padding_frames = int(self.padding_duration_ms / self.frame_duration_ms)

        # State
        self._triggered = False
        self._voiced_frames = []
        self._ring_buffer = collections.deque(maxlen=num_padding_frames)
        self._resample_buffer = b''

        self._output_queues['audio'] = QueueSlot(self, 'output', datatype='audio')
        self._output_queues['default'] = self._output_queues['audio']

        self.vad = webrtcvad.Vad(self.aggressiveness)

        utils.config.debug_print(
                f"[{self.name}] WebRTCVAD ready — "
                f"aggressiveness={self.aggressiveness}, "
                f"frame={self.frame_duration_ms}ms, "
                f"padding={self.padding_duration_ms}ms "
                f"({num_padding_frames} frames), "
                f"frame_bytes={self._frame_bytes}"
            )


middle_modules_class['webrtc_vad'] = WebRTCVAD
