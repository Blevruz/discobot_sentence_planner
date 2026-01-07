# chatbot/input_methods/dummy.py
from utils.module_management import DummyModule

import multiprocessing
import threading
import time


class DummyInput(DummyModule):

    # Input queue is not used
    @property
    def input_queue(self):
        raise "Attempted to read input queue on input module"
        return None
    @input_queue.setter
    def input_queue(self, queue):
        raise "Attempted to write to input queue on input module"
    def _create_input_queue(self): 
        raise "Attempted to create input queue on input module"
    def _add_input_queue(self, queue):
        raise "Attempted to add input queue on input module"


    def action(self, i):
        return

    def get_input(self):
        return self.output_queue.get()

    def __init__(self, name="dummy_input", queue=None):
        DummyModule.__init__(self, name)
        self.type = "input"

        # An input module is the end point of the pipeline, so it has no need
        # for an output queue
        self.loop_type = "process"

        self._input_queues.append(None)
        self._output_queues.append(None)

input_methods_class = dict()
input_methods_class['dummy'] = DummyInput
