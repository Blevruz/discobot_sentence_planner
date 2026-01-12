# chatbot/input_methods/helloworld.py
from input_methods.dummy import DummyInput, input_methods_class

import multiprocessing
import threading
import time


class HelloWorldInput(DummyInput):

    def action(self, i):
        self.output_queue.put(f"Hello world! {i}")
        time.sleep(self.delay)

    def __init__(self, name="helloworld", queue=None, delay=1.0, timeout=1.0):
        DummyInput.__init__(self, name)
        self.datatype_out = "string"
        self.delay = delay
        self.timeout = timeout

input_methods_class['helloworld'] = HelloWorldInput
