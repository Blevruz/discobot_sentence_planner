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
        try:
            if self.verbose:
                print(f"READ ATTEMPT N°{i}")
            print(f"SYS> {self.input_queue.get(timeout=self.timeout)}")
            time.sleep(self.delay)
        except:
            if self.verbose:
                print(f"READ ATTEMPT N°{i} FAILED")
            time.sleep(self.delay)
            return

    def put_output(self, message):
        self.input_queue.put(message)

    def __init__(self, name = "dummy_output", delay=1.0, timeout=1.0):
        DummyModule.__init__(self, name)
        self.type = "output"
        self.delay = delay
        self.timeout = timeout
        # An output module is the end point of the pipeline, so it doesn't
        # need an output queue
        self.loop_type = 'thread'

        self._input_queues.append(None)
        self._output_queues.append(None)


output_methods_class = dict()
output_methods_class['dummy'] = DummyOutput
#output_methods_class['dummy'] = lambda name: DummyOutput(name, delay=0.0, timeout=0.0)
