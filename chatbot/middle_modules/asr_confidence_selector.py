# chatbot/middle_modules/asr_confidence_selector.py

from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import time
import utils.config

class ASRConfidenceSelector(DummyMiddle):
    """Selects the transcription from multiple ASR modules based on confidence."""

    def __init__(self, name="asr_selector", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = "thread"

        self.num_models = args.get("num_models", 2)
        self.window = args.get("window", 0.2)  # seconds to wait for competitors

        # Create dynamic input queues
        self.text_queues = []
        self.conf_queues = []

        for i in range(self.num_models):
            tq = QueueSlot(self, 'input', datatype='string', name=f"text_{i}")
            cq = QueueSlot(self, 'input', datatype='float', name=f"conf_{i}")
            self._input_queues[f"text_{i}"] = tq
            self._input_queues[f"conf_{i}"] = cq
            self.text_queues.append(tq)
            self.conf_queues.append(cq)

        #self._output_queues['output'] = QueueSlot(self, 'output', datatype='string')
        #self._output_queues['default'] = self._output_queues['output']

    def action(self, i):
        candidates = []

        # Try to gather inputs from all ASR modules
        for idx in range(self.num_models):
            tq = self.text_queues[idx][0]
            cq = self.conf_queues[idx][0]

            text = tq.get()
            conf = cq.get()
            if text and conf:
                candidates.append((conf, text, idx))

        if not candidates:
            return

        # Wait a bit for slower ASR modules
        time.sleep(self.window)

        # Gather late arrivals
        for idx in range(self.num_models):
            tq = self.text_queues[idx][0]
            cq = self.conf_queues[idx][0]

            text = tq.get()
            conf = cq.get()
            if text and conf:
                candidates.append((conf, text, idx))

        # Select best
        best_conf, best_text, best_idx = max(candidates, key=lambda x: x[0])

        if utils.config.verbose:
            utils.config.debug_print(
                f"[ASRSelector] Chose model {best_idx} with conf={best_conf:.3f}: '{best_text}'"
            )

        self.output_queue.put(best_text)

middle_modules_class['asr_confidence_selector'] = ASRConfidenceSelector
