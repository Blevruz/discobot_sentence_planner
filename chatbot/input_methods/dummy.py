from utils.module_management import DummyModule

import multiprocessing
import threading
import time


class DummyInput(DummyModule):
    def __init__(self, name, queue=None, delay=1.0, timeout=1.0):
        DummyModule.__init__(self, name)
        self.delay = delay
        self.timeout = timeout
        # An input module is the end point of the pipeline, so it has no need
        # for an output queue
        self.input_queue = None
        self.input_loop = multiprocessing.Process(target=self._input_loop)
        self.stopped = False

    def _input_loop(self):
        i = 0
        while not self.stopped:
            self.output_queue.put(f"Hello world! {i}")
            i += 1
            time.sleep(self.delay)

    def start_loop(self, verbose):
        self.stopped = False
        if verbose:
            print(f"[DEBUG] Starting input loop for {self.name}")
        self.input_loop.start()

    def stop_loop(self, verbose):
        self.stopped = True
        if verbose:
            print(f"[DEBUG] Stopping input loop for {self.name}")
        if type(self.input_loop) is threading.Thread:
            self.input_loop.join(self.timeout)
        elif type(self.input_loop) is multiprocessing.Process:
            self.input_loop.terminate()
        else:
            raise ValueError(f"Unknown type for input loop: {type(self.input_loop)}")

    def get_input(self):
        return self.output_queue.get()

input_methods_class = dict()
input_methods_class['dummy'] = DummyInput
