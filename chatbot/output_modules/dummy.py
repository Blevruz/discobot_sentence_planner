# chatbot/output_modules/dummy.py
from utils.dummy_module import DummyModule

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


output_modules_class = dict()
output_modules_class['dummy'] = DummyOutput
