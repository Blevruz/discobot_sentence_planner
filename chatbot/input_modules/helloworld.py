# chatbot/input_modules/helloworld.py
from input_modules.dummy import DummyInput, input_modules_class

import multiprocessing
import threading
import time


class HelloWorldInput(DummyInput):
    """Hello World module. Outputs a string at regular intervals"""

    def action(self, i):
        """Output a numbered string, then sleeps"""
        self.output_queue.put(f"Hello world! {i}")
        time.sleep(self.delay)

    def __init__(self, name="helloworld", **args):
        DummyInput.__init__(self, name, **args)
        self._loop_type = 'thread'
        self.datatype_out = "string"
        self.delay = args.get('delay', 1.0)
        self.timeout = args.get('timeout', 1.0)

input_modules_class['helloworld'] = HelloWorldInput
