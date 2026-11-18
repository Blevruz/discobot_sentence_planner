import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

import utils.config
from middle_modules.dummy import middle_modules_class  # noqa: E402
from middle_modules.silero_vad import SileroVAD  # noqa: E402
from utils.dummy_module import DummyModule  # noqa: E402

CHUNK = 512          # samples per Silero chunk at 16 kHz (32 ms)
QUIET = 0.05         # "probabilities" far from the 0.5 and 0.35 thresholds
SPEECH = 0.9
DIP = 0.4            # between the thresholds
SILENT = 0.1         # below neg_threshold


class FakeModel:
    def __init__(self):
        self.resets = 0

    def reset_states(self):
        self.resets += 1


class FakeSilero(SileroVAD):
    """SileroVAD without torch: each chunk is a constant whose value is the
    speech probability the 'model' reports for it."""

    def _load_model(self):
        return FakeModel()

    def _speech_prob(self, chunk):
        return float(chunk[0])


def pcm(*probs):
    """Audio with one 32 ms chunk per probability."""
    return b''.join(
        np.full(CHUNK, int(p * 32768), dtype=np.int16).tobytes() for p in probs)


class SileroVADTests(unittest.TestCase):
    def make(self, **args):
        self.vad = FakeSilero(**args)
        self.sinks = {}
        for slot in ('audio', 'speech_start', 'speech_end'):
            self.sinks[slot] = DummyModule("sink_" + slot)
            self.vad.link_to(self.sinks[slot], from_slot=slot)
        return self.vad

    def drain(self, slot):
        """Everything that arrives on `slot`. Multiprocessing queues are fed
        by a thread, and a big item only goes through the pipe as fast as it
        is read, so keep reading until nothing has come for a while."""
        out = []
        quiet_since = time.time()
        while time.time() - quiet_since < 0.15:
            x = self.sinks[slot].input_queue.get()
            if x is None:
                time.sleep(0.005)
            else:
                out.append(x)
                quiet_since = time.time()
        return out

    def test_module_is_registered_and_imports_without_torch(self):
        self.assertIs(middle_modules_class['silero_vad'], SileroVAD)

    def test_one_utterance_with_padding_and_both_signals(self):
        vad = self.make()
        vad._feed(pcm(*[QUIET] * 20, *[SPEECH] * 40, *[QUIET] * 40))
        audio = self.drain('audio')
        self.assertEqual(len(audio), 1)
        # 9 chunks of pre-roll (300 ms), 40 of speech, 9 of trailing pad
        self.assertEqual(len(audio[0]), (9 + 40 + 9) * CHUNK)
        self.assertEqual(audio[0].dtype, np.float32)
        self.assertEqual(self.drain('speech_start'), [True])
        self.assertEqual(self.drain('speech_end'), [True])

    def test_noise_burst_is_dropped_and_model_reset(self):
        vad = self.make()
        before = vad.model.resets
        vad._feed(pcm(*[QUIET] * 5, SPEECH, SPEECH, *[QUIET] * 40))
        self.assertEqual(self.drain('audio'), [])
        self.assertEqual(self.drain('speech_start'), [])
        self.assertEqual(self.drain('speech_end'), [])
        self.assertEqual(vad.model.resets, before + 1)

    def test_speech_start_waits_for_min_speech(self):
        vad = self.make()
        vad._feed(pcm(*[SPEECH] * 7))  # 7 x 32 ms < 250 ms
        self.assertEqual(self.drain('speech_start'), [])
        vad._feed(pcm(SPEECH))
        self.assertEqual(self.drain('speech_start'), [True])

    def test_model_reset_after_each_utterance(self):
        vad = self.make()
        before = vad.model.resets
        for _ in range(2):
            vad._feed(pcm(*[SPEECH] * 20, *[QUIET] * 30))
        self.assertEqual(len(self.drain('audio')), 2)
        self.assertEqual(vad.model.resets, before + 2)

    def test_hysteresis_keeps_utterance_whole(self):
        vad = self.make()
        # 1.3 s hovering between the two thresholds, then 0.3 s of real
        # silence-ish dip (shorter than silence_threshold_ms): still one
        vad._feed(pcm(*[SPEECH] * 10, *[DIP] * 40, *[SILENT] * 10,
                      *[SPEECH] * 10, *[QUIET] * 40))
        self.assertEqual(len(self.drain('audio')), 1)

    def test_long_silence_splits_utterances(self):
        vad = self.make()
        vad._feed(pcm(*[SPEECH] * 10, *[SILENT] * 25, *[SPEECH] * 10,
                      *[SILENT] * 25))
        self.assertEqual(len(self.drain('audio')), 2)

    def test_dip_threshold_is_configurable(self):
        vad = self.make(neg_threshold=0.45)  # DIP now counts as silence
        vad._feed(pcm(*[SPEECH] * 10, *[DIP] * 25, *[SPEECH] * 10,
                      *[DIP] * 25))
        self.assertEqual(len(self.drain('audio')), 2)

    def test_maximum_length_cuts_continuous_speech(self):
        vad = self.make(max_utterance_s=1.0)  # 31 chunks
        vad._feed(pcm(*[SPEECH] * 100, *[QUIET] * 40))
        audio = self.drain('audio')
        self.assertGreaterEqual(len(audio), 3)
        self.assertTrue(all(len(a) <= 31 * CHUNK for a in audio))

    def test_any_input_chunking_gives_the_same_result(self):
        stream = pcm(*[QUIET] * 20, *[SPEECH] * 30, *[QUIET] * 40)
        whole = self.make()
        whole._feed(stream)
        expected = self.drain('audio')
        for size in (4800, 1000, 7):
            vad = self.make()
            for i in range(0, len(stream), size):
                vad._feed(stream[i:i + size])
            got = self.drain('audio')
            self.assertEqual(len(got), 1, size)
            np.testing.assert_array_equal(got[0], expected[0])

    def test_8khz_uses_256_sample_chunks(self):
        vad = self.make(sample_rate=8000)
        self.assertEqual(vad._chunk_samples, 256)

    def test_bad_arguments_are_refused(self):
        for args in ({'sample_rate': 44100}, {'source': 'web'},
                     {'vad_threshold': 0.3, 'neg_threshold': 0.4},
                     {'neg_threshold': 0}):
            with self.assertRaises(ValueError, msg=args):
                FakeSilero(**args)

    def test_backlog_is_skipped_while_idle(self):
        vad = self.make(max_backlog_s=2.0)
        with mock.patch.object(utils.config, 'debug_print') as log:
            vad._feed(pcm(*[QUIET] * 300))  # 9.6 s of audio at once
        self.assertGreater(vad.skipped_audio_s, 7.0)
        self.assertLess(vad.skipped_audio_s, 8.0)
        self.assertTrue(any('skipped' in str(c) for c in log.call_args_list))
        self.assertLess(len(vad._resample_buffer), CHUNK * 2)

    def test_speech_after_a_skipped_backlog_is_still_found(self):
        vad = self.make(max_backlog_s=2.0)
        vad._feed(pcm(*[QUIET] * 300, *[SPEECH] * 20, *[QUIET] * 40))
        self.assertEqual(len(self.drain('audio')), 1)

    def test_nothing_is_skipped_during_an_utterance(self):
        vad = self.make(max_backlog_s=2.0)
        vad._feed(pcm(*[SPEECH] * 10))           # utterance in progress
        vad._feed(pcm(*[SPEECH] * 150, *[QUIET] * 40))  # 4.8 s at once
        self.assertEqual(vad.skipped_audio_s, 0)
        audio = self.drain('audio')
        self.assertEqual(len(audio), 1)
        self.assertGreaterEqual(len(audio[0]), 160 * CHUNK)

    def test_backlog_limit_can_be_disabled(self):
        vad = self.make(max_backlog_s=None)
        vad._feed(pcm(*[QUIET] * 300))
        self.assertEqual(vad.skipped_audio_s, 0)

    def test_action_takes_everything_that_is_waiting(self):
        vad = self.make()
        src = DummyModule("src")
        src.link_to(vad)
        stream = pcm(*[QUIET] * 5, *[SPEECH] * 20, *[QUIET] * 40)
        for i in range(0, len(stream), 4800):
            src.output_queue.put(stream[i:i + 4800])
        time.sleep(0.2)
        vad.action(0)  # one call
        self.assertEqual(len(self.drain('audio')), 1)

    def test_load_statistics_are_logged(self):
        class Slow(FakeSilero):
            def _speech_prob(self, chunk):
                time.sleep(0.002)
                return float(chunk[0])

        vad = Slow(stats_interval_s=0.05)
        with mock.patch.object(utils.config, 'debug_print') as log:
            for _ in range(5):
                vad._feed(pcm(*[QUIET] * 10))
        reports = [str(c) for c in log.call_args_list if 'real-time factor' in str(c)]
        self.assertTrue(reports)
        self.assertIn('ms/chunk', reports[0])
        self.assertNotIn('FALLING BEHIND', reports[0])  # 2 ms per 32 ms chunk

    def test_falling_behind_is_flagged(self):
        class VerySlow(FakeSilero):
            def _speech_prob(self, chunk):
                time.sleep(0.04)  # slower than the 32 ms of audio
                return float(chunk[0])

        vad = VerySlow(stats_interval_s=0.1)
        with mock.patch.object(utils.config, 'debug_print') as log:
            vad._feed(pcm(*[QUIET] * 6))
        self.assertTrue(any('FALLING BEHIND' in str(c) for c in log.call_args_list))

    def test_non_bytes_input_does_not_crash_the_loop(self):
        vad = self.make()
        src = DummyModule("src")
        src.link_to(vad)
        src.output_queue.put(np.zeros(CHUNK, dtype=np.float32))
        time.sleep(0.1)
        vad.action(0)  # must not raise
        self.assertEqual(self.drain('audio'), [])


if __name__ == '__main__':
    unittest.main()
