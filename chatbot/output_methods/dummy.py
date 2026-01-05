from utils.module_management import DummyModule

import multiprocessing
import threading
import time


class DummyOutput(DummyModule):
    def __init__(self, name, delay=1.0, timeout=1.0):
        DummyModule.__init__(self, name)
        self.delay = delay
        self.timeout = timeout
        # An output module is the end point of the pipeline, so it doesn't
        # need an output queue
        self.output_queue = None
        #self.output_loop = multiprocessing.Process(target=self._output_loop)
        #self.stopped = False
        self.output_loop = threading.Thread(target=self._output_loop)
        self.stopped = threading.Event()

    def _output_loop(self):
        while not self.is_stopped():
            try:
                print(self.input_queue.get(timeout=self.timeout))
                time.sleep(self.delay)
            except:
                pass

    def start_loop(self, verbose):
        if type(self.output_loop) is not threading.Thread:
            self.stopped = False
        if verbose:
            print(f"[DEBUG] Starting output loop for {self.name}")
        self.output_loop.start()

    def stop_loop(self, verbose):
        if verbose:
            print(f"[DEBUG] Stopping output loop for {self.name}")
        if type(self.output_loop) is threading.Thread:
            self.stopped.set()
            self.output_loop.join(self.timeout)
        elif type(self.output_loop) is multiprocessing.Process:
            self.stopped = True
            self.output_loop.terminate()
        else:
            raise ValueError(f"Unknown type for output loop: {type(self.output_loop)}")

    def is_stopped(self):
        if type(self.stopped) is threading.Event:
            return self.stopped.is_set()
        else:
            return self.stopped

    def put_output(self, message):
        self.input_queue.put(message)

output_methods_class = dict()
output_methods_class['dummy'] = DummyOutput
