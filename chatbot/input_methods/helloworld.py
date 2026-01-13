# chatbot/input_methods/helloworld.py
from input_methods.dummy import DummyInput, input_methods_class

import multiprocessing
import threading
import time


class HelloWorldInput(DummyInput):

    def action(self, i):
        self.output_queue.put(f"Hello world! {i}")
        time.sleep(self.delay)

    def __init__(self, name="helloworld", **args):
        DummyInput.__init__(self, name)
        self._datatype_out = "string"
        self.delay = args.get('delay', 1.0)
        self.timeout = args.get('timeout', 1.0)

input_methods_class['helloworld'] = HelloWorldInput
