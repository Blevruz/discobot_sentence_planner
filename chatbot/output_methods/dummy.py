# chatbot/output_methods/dummy.py
from utils.module_management import DummyModule

import multiprocessing
import threading
import time


class DummyOutput(DummyModule):

    # Output queue is not used
    @property
    def output_queue(self):
        raise "Attempted to read output queue on output module"
        return None
    @output_queue.setter
    def output_queue(self, queue):
        raise "Attempted to write to output queue on output module"
    def _create_output_queue(self): 
        raise "Attempted to create output queue on output module"
    def _add_output_queue(self, queue):
        raise "Attempted to add output queue on output module"

    def action(self, i):
        return

    def put_output(self, message):
        self.input_queue.put(message)

    def __init__(self, name = "dummy_output"):
        DummyModule.__init__(self, name)
        self.type = "output"
        # An output module is the end point of the pipeline, so it doesn't
        # need an output queue

        self._input_queues.append(None)
        self._output_queues.append(None)


output_methods_class = dict()
output_methods_class['dummy'] = DummyOutput
