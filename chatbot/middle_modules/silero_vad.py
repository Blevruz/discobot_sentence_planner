# chatbot/middle_modules/silero_vad.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config
import numpy as np
import math
import time

class SileroVAD(DummyMiddle):
    """Voice Activity Detection using Silero VAD.

    Sits between a raw PCM audio source (e.g. PyAudioInput) and a
    transcriber (e.g. FasterWhisper). Accumulates incoming int16 PCM
    byte chunks, detects speech boundaries, and flushes complete
    utterances downstream as float32 numpy arrays.

    Speech is decided per chunk (32 ms at 16 kHz) from Silero's speech
    probability, with the logic of Silero's own reference implementation.
      * an utterance starts when the probability reaches `vad_threshold`, and
        is only kept if it holds at least `min_speech_ms` of speech, so that
        a click or a burst of noise is dropped instead of being transcribed;
      * it goes on while the probability stays above the lower
        `neg_threshold` (hysteresis), so a dip between two words does not cut
        it, and ends after `silence_threshold_ms` below that;
      * it is cut after `max_utterance_s` so that continuous noise cannot
        grow the buffer without bound;
      * the model's recurrent state is reset after every utterance.

    Parameters
    ----------
    sample_rate : int
        Must match the upstream source: 8000 or 16000. Default 16000.
    vad_threshold : float
        Silero speech probability threshold (0.0–1.0). Default 0.5.
    neg_threshold : float
        Probability below which a chunk counts as silence. Default None,
        meaning vad_threshold - 0.15, at least 0.01
    min_speech_ms : int
        Minimum length of speech in ms. Default 250.
    speech_pad_ms : int
        Audio kept before speech onset and after speech end (ms).
        Prevents clipping of utterance edges. Default 300.
    silence_threshold_ms : int
        How long silence must persist after speech before the utterance
        is flushed downstream. Default 700.
    max_utterance_s : float
        Longest utterance; a longer one is cut there. Default 30, the size of
        Whisper's decoding window.
    source : str
        Where the model comes from: "pip" (the `silero-vad` package, which
        bundles the model and works offline), "hub" (torch.hub, which needs
        to reach GitHub unless already cached) or "auto" (pip if installed,
        else hub). Default "auto".
    model_path, model_name : str
        torch.hub repository and model, for the "hub" source.
    torch_threads : int or None
        If set, passed to torch.set_num_threads. Silero recommends 1, but
        this is process-wide, so it is left alone by default.
    idle_sleep_s : float
        Seconds to sleep when the input queue is empty, to avoid
        burning CPU in a busy-wait loop. Default 0.005.

    Inputs
    ------
    - default: audio
        int16 PCM bytes, in chunks of any size.

    Outputs
    -------
    - default / audio: audio
        One float32 array in [-1, 1] per utterance: `speech_pad_ms` of audio
        before the speech, the speech, and `speech_pad_ms` after it.
    - speech_start: any
        True when an utterance is confirmed (after `min_speech_ms`).
    - speech_end: any
        True when the utterance has been sent.
    """

    def _load_model(self):
        if self.torch_threads:
            import torch
            torch.set_num_threads(self.torch_threads)
        if self.source in ("auto", "pip"):
            try:
                from silero_vad import load_silero_vad
                return load_silero_vad()
            except ImportError:
                if self.source == "pip":
                    raise
        import torch
        model, _ = torch.hub.load(
            repo_or_dir=self.model_path,
            model=self.model_name,
            force_reload=False,
            trust_repo=True
        )
        return model

    def _speech_prob(self, chunk_f32):
        """Silero speech probability for one float32 chunk of exactly
        self._chunk_samples samples."""
        import torch
        with torch.no_grad():
            return self.model(torch.from_numpy(chunk_f32),
                              self.sample_rate).item()

    def _reset_model(self):
        """Silero is recurrent: forget the previous utterance."""
        reset = getattr(self.model, 'reset_states', None)
        if reset is not None:
            reset()

    def _clear_utterance(self):
        self._active = False
        self._confirmed = False
        self._audio_buffer = []
        self._pad_buffer = []
        self._voiced_chunks = 0
        self._silence_chunks = 0
        self._reset_model()

    def _emit(self, slot, item):
        if len(self._output_queues[slot]) > 0:
            self._output_queues[slot].put(item)


    def _finish_utterance(self):
        """The utterance is over (silence, or maximum length). Send it if it
        held enough speech, drop it otherwise."""
        chunks = self._audio_buffer
        if self._confirmed:
            # Keep at most speech_pad_ms of the trailing silence
            extra = self._silence_chunks - self._pad_chunks
            if extra > 0:
                chunks = chunks[:-extra]
            utterance = np.concatenate(chunks)
            duration = len(utterance) / self.sample_rate
            utils.config.debug_print(
                f"[{self.name}] Flushing utterance ({duration:.2f}s)"
            )
            self._emit('audio', utterance)
            self._emit('speech_end', True)
        else:
            utils.config.debug_print(
                f"[{self.name}] Dropped noise burst "
                f"({self._voiced_chunks} voiced chunks < "
                f"{self._min_speech_chunks})"
            )
        self._clear_utterance()

    def _process_chunk(self, chunk):
        t0 = time.perf_counter()
        prob = self._speech_prob(chunk)
        self._note_chunk_time(time.perf_counter() - t0)

        if not self._active:
            if prob >= self.vad_threshold:
                # Possible onset: prepend the pre-roll
                self._active = True
                self._audio_buffer = list(self._pad_buffer) + [chunk]
                self._pad_buffer = []
                self._voiced_chunks = 1
                self._silence_chunks = 0
            else:
                # Outside speech: maintain rolling pre-roll window
                self._pad_buffer.append(chunk)
                if len(self._pad_buffer) > self._pad_chunks:
                    self._pad_buffer.pop(0)
                return
        else:
            self._audio_buffer.append(chunk)
            if prob >= self.vad_threshold:
                self._voiced_chunks += 1
                self._silence_chunks = 0
            elif prob >= self.neg_threshold:
                # Between the two thresholds: neither new speech nor silence
                self._silence_chunks = 0
            else:
                self._silence_chunks += 1

        if not self._confirmed and self._voiced_chunks >= self._min_speech_chunks:
            self._confirmed = True
            self._emit('speech_start', True)
            utils.config.debug_print(f"[{self.name}] Speech onset detected")

        if self._silence_chunks >= self._silence_chunks_needed \
                or len(self._audio_buffer) >= self._max_chunks:
            self._finish_utterance()

    def _note_chunk_time(self, seconds):
        """Keep load statistics and log them every stats_interval_s."""
        self._stat_chunks += 1
        self._stat_compute_s += seconds
        self._stat_max_s = max(self._stat_max_s, seconds)
        if not self.stats_interval_s:
            return
        now = time.perf_counter()
        if now - self._stat_t0 < self.stats_interval_s:
            return
        audio_s = self._stat_chunks * self._chunk_samples / self.sample_rate
        rtf = self._stat_compute_s / audio_s
        backlog_s = len(self._resample_buffer) / 2 / self.sample_rate
        behind = rtf >= 0.8 or backlog_s > 1.0
        utils.config.debug_print(
            f"[{self.name}] Processed {audio_s:.1f}s of audio in "
            f"{self._stat_compute_s:.2f}s (real-time factor {rtf:.2f}), "
            f"{1000 * self._stat_compute_s / self._stat_chunks:.1f} ms/chunk "
            f"(max {1000 * self._stat_max_s:.0f}), backlog {backlog_s:.1f}s"
            + (" - FALLING BEHIND REAL TIME" if behind else "")
        )
        self._stat_t0 = now
        self._stat_chunks = 0
        self._stat_compute_s = 0.0
        self._stat_max_s = 0.0

    def _skip_backlog(self, chunk_bytes):
        """Throw away the oldest audio, keeping max_backlog_s of it."""
        keep = (self._max_backlog_bytes // chunk_bytes) * chunk_bytes
        drop = ((len(self._resample_buffer) - keep) // chunk_bytes) * chunk_bytes
        if drop <= 0:
            return
        del self._resample_buffer[:drop]
        seconds = drop / 2 / self.sample_rate
        self.skipped_audio_s += seconds
        # The audio is no longer continuous
        self._pad_buffer = []
        self._reset_model()
        utils.config.debug_print(
            f"[{self.name}] WARNING: behind real time, skipped {seconds:.1f}s "
            f"of audio ({self.skipped_audio_s:.1f}s in total)"
        )


    def _feed(self, raw):
        """Take int16 PCM bytes of any length."""
        # Silero requires exactly _chunk_samples samples per call.
        # Accumulate a buffer to handle arbitrary upstream chunk sizes
        # (e.g. PyAudio's 4800-frame default).
        self._resample_buffer += raw
        bytes_needed = self._chunk_samples * 2  # int16 = 2 bytes/sample

        while len(self._resample_buffer) >= bytes_needed:
            if (self._max_backlog_bytes and not self._active
                    and len(self._resample_buffer) > self._max_backlog_bytes):
                self._skip_backlog(bytes_needed)
            chunk_bytes = bytes(self._resample_buffer[:bytes_needed])
            del self._resample_buffer[:bytes_needed]
            chunk = np.frombuffer(chunk_bytes, dtype=np.int16) \
                      .astype(np.float32) / 32768.0
            self._process_chunk(chunk)


    def action(self, i):
        try:
            raw = self.input_queue.get()
            # Queue is non-blocking; sleep briefly on empty to avoid
            # spinning and burning CPU
            if raw is None:
                time.sleep(self.idle_sleep_s)
                return

            # Take everything that is waiting, so that a backlog shows up in
            # self._resample_buffer where it is measured and bounded
            pieces = [raw]
            while len(pieces) < 1000:
                more = self.input_queue.get()
                if more is None:
                    break
                pieces.append(more)
            for piece in pieces:
                if isinstance(piece, (bytes, bytearray)):
                    self._feed(piece)
                else:
                    utils.config.debug_print(
                        f"[{self.name}] Dropped non-bytes input "
                        f"({type(piece).__name__})")

        except Exception as e:
            utils.config.debug_print(f"Error in SileroVAD: {e}")

    def __init__(self, name="silero_vad", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "audio"
        self.datatype_out = "audio"

        self.sample_rate = args.get('sample_rate', 16000)
        self.vad_threshold = args.get('vad_threshold', 0.5)
        neg = args.get('neg_threshold', None)
        self.neg_threshold = max(self.vad_threshold - 0.15, 0.01) \
            if neg is None else neg
        self.min_speech_ms = args.get('min_speech_ms', 250)
        self.speech_pad_ms = args.get('speech_pad_ms', 300)
        self.silence_threshold_ms = args.get('silence_threshold_ms', 700)
        self.max_utterance_s = args.get('max_utterance_s', 30)
        self.idle_sleep_s = args.get('idle_sleep_s', 0.005)
        self.source = args.get('source', 'auto')
        self.torch_threads = args.get('torch_threads', 1)
        self.max_backlog_s = args.get('max_backlog_s', 5.0)
        self.stats_interval_s = args.get('stats_interval_s', 10)

        self.model_path = args.get('model_path', 'snakers4/silero-vad')
        self.model_name = args.get('model_name', 'silero_vad')

        if self.sample_rate not in (8000, 16000):
            raise ValueError(
                f"sample_rate must be 8000 or 16000, not {self.sample_rate}")
        if self.source not in ("auto", "pip", "hub"):
            raise ValueError(
                f"source must be 'auto', 'pip' or 'hub', not {self.source!r}")
        if not 0 < self.neg_threshold <= self.vad_threshold <= 1:
            raise ValueError(
                "need 0 < neg_threshold <= vad_threshold <= 1, got "
                f"{self.neg_threshold} and {self.vad_threshold}")

        # Silero VAD requires exactly 512 samples at 16kHz, 256 at 8kHz
        self._chunk_samples = 512 if self.sample_rate == 16000 else 256
        chunk_ms = (self._chunk_samples / self.sample_rate) * 1000

        self._pad_chunks = max(1, int(self.speech_pad_ms / chunk_ms))
        self._silence_chunks_needed = max(1, int(self.silence_threshold_ms / chunk_ms))
        self._min_speech_chunks = max(1, math.ceil(self.min_speech_ms / chunk_ms))
        self._max_chunks = max(1, int(self.max_utterance_s * 1000 / chunk_ms))

        # Bytes of audio (int16) after which the oldest is skipped; 0 = never
        self._max_backlog_bytes = int(self.max_backlog_s * self.sample_rate) * 2 \
            if self.max_backlog_s else 0

        # State
        self._active = False        # between a possible onset and the end
        self._confirmed = False     # ... and it holds enough speech
        self._audio_buffer = []     # accumulates chunks during speech
        self._pad_buffer = []       # rolling pre-roll window
        self._voiced_chunks = 0     # chunks at or above vad_threshold
        self._silence_chunks = 0    # consecutive silent chunks since speech
        self._resample_buffer = bytearray()  # mismatched upstream chunk sizes
        self.skipped_audio_s = 0.0
        self._stat_t0 = time.perf_counter()
        self._stat_chunks = 0
        self._stat_compute_s = 0.0
        self._stat_max_s = 0.0

        # Same outputs as WebRTCVAD. DummyModule creates 'output' as
        # datatype='any', so we add our named slots and remap 'default'.
        self._output_queues['audio'] = QueueSlot(self, 'output', datatype='audio')
        self._output_queues['default'] = self._output_queues['audio']
        self._output_queues['speech_start'] = QueueSlot(self, 'output', datatype='any')
        self._output_queues['speech_end'] = QueueSlot(self, 'output', datatype='any')

        utils.config.debug_print(f"[{self.name}] Loading Silero VAD model "
                                 f"(source={self.source})")
        self.model = self._load_model()
        if hasattr(self.model, 'eval'):
            self.model.eval()
        self._reset_model()

        utils.config.debug_print(
                f"[{self.name}] Silero VAD ready — "
                f"threshold={self.vad_threshold}/{self.neg_threshold}, "
                f"min_speech={self.min_speech_ms}ms, "
                f"silence={self.silence_threshold_ms}ms, "
                f"pad={self.speech_pad_ms}ms, "
                f"chunk={self._chunk_samples} samples"
            )


middle_modules_class['silero_vad'] = SileroVAD
