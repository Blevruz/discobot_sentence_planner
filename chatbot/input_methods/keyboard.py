from input_methods.dummy import DummyInput, input_methods_class
from multiprocessing import Queue
import queue
import threading

class KeyboardInput(DummyInput):
    def __init__(self, name):
        DummyInput.__init__(self, name)
        self.name = name
        self.input_loop = threading.Thread(target=self._input_loop)

    def _input_loop(self):
        while True:
            self.output_queue.put(input())

input_methods_class = dict()
input_methods_class['keyboard'] = KeyboardInput
