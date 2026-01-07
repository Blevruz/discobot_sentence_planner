# chatbot/utils/module_management.py
import multiprocessing
import threading

##  We want to have an arbitrary number of input and output queues
#   and be able to work with a set of assumptions in specific modules
#   EXAMPLE CASE 1: Module has 1 input queue and 1 output queue.
#       - We could have a list of queue that is only accessed through getters
#           and setters, thus restricting us to only one input and output queue
#           which could work elegantly with "property" decorators.
#   EXAMPLE CASE 2: Module has n input queues of the same type and 1 output
#       queue, to which it writes packaged messages.
#       - This cannot be done with a "property" decorator. 
#   EXAMPLE CASE 3: Module has 1 input queue of type A and 1 input queue of
#       type B, as well as 1 output queue of type C and 1 output queue of
#       type D.
#       - It becomes necessary to distinguish between the different types of
#           queues. This may warrant a queue class with type information.

#   Maybe rather than directly manipulate queues, we could have methods that
#   handle connecting two modules. Example: 
#       module_in.queue_to(module_out)
#       module_in.queue_from(module_out)
#   Within the methods, they would call the receiving module's methods to add
#   queues appropriately (or not! Error handling would be necessary).
#       Mockup:
#       def queue_to(self, module_out):
#           module_out.add_input_queue(self._create_output_queue())
#       def _create_output_queue(self): # for our 1 input-1 output case
#           self._output_queues[0] = multiprocessing.Queue()
#           return self._output_queues[0]
#       def add_input_queue(self, queue):   # for our n input-1 output case
#           self._input_queues.append(queue)



class DummyModule:
    def __init__(self, name = "dummy", verbose=False):
        self._type = 'dummy'
        self._name = name
        self.verbose = verbose
        # Set of queues we only read from
        self._input_queues = list()
        # Set of queues we only write to
        self._output_queues = list()
        self._loop_type = 'blocking'

    @property
    def type(self):
        return self._type
    @type.setter
    def type(self, type):
        self._type = type

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, name):
        self._name = name

    @property
    def input_queue(self):
        return self._input_queues[0]
    @input_queue.setter
    def input_queue(self, queue):
        self._input_queues[0] = queue

    @property
    def output_queue(self):
        return self._output_queues[0]
    @output_queue.setter
    def output_queue(self, queue):
        self._output_queues[0] = queue

    def _create_input_queue(self): 
        if len(self._input_queues) > 0:
            self._input_queues[0] = multiprocessing.Queue()
        else:
            self._input_queues.append(multiprocessing.Queue())
        if self.verbose:
            print(f"[DEBUG] Created input queue {self._input_queues[0]} for {self.name}")
        return self._input_queues[0]

    def _create_output_queue(self): 
        if len(self._output_queues) > 0:
            self._output_queues[0] = multiprocessing.Queue()
        else:
            self._output_queues.append(multiprocessing.Queue())
        if self.verbose:
            print(f"[DEBUG] Created output queue {self._output_queues[0]} for {self.name}")
        return self._output_queues[0]

    def add_input_queue(self, queue):
        if self.verbose:
            print(f"[DEBUG] Assigning input queue {queue} to {self.name}")
        if len(self._input_queues) > 0:
            self._input_queues[0] = queue
        else:
            self._input_queues.append(queue)

    def add_output_queue(self, queue):
        if self.verbose:
            print(f"[DEBUG] Assigning output queue {queue} to {self.name}")
        if len(self._output_queues) > 0:
            self._output_queues[0] = queue
        else:
            self._output_queues.append(queue)

    def link_to(self, other):
        if self.verbose:
            print(f"[DEBUG] Setting {self.name}'s output queue as {other.name}'s input queue, of types {type(self.output_queue)} and {type(other.input_queue)}")
        other.add_input_queue(self._create_output_queue())

    def link_from(self, other):
        if self.verbose:
            print(f"[DEBUG] Setting {self.name}'s input queue as {other.name}'s output queue, of types {type(self.input_queue)} and {type(other.output_queue)}")
        other.add_output_queue(self._create_input_queue())

    def _loop(self):
        i = 0
        while not self.is_stopped():
            self.action(i)
            i += 1

    def start_loop(self):
        if self.verbose:
            print(f"[DEBUG] Starting {self.type} loop for {self.name}")
        self.stopped = threading.Event()
        if self.loop_type == 'blocking':
            self._loop()
            return
        if self.loop_type == 'thread':
            self.loop = threading.Thread(target=self._loop)
        elif self.loop_type == 'process':
            self.loop = multiprocessing.Process(target=self._loop)
        self.loop.start()

    def stop_loop(self):
        if self.verbose:
            print(f"[DEBUG] Stopping {self.type} loop for {self.name}")
        self.stopped.set()
        if type(self.loop) is threading.Thread:
            self.loop.join(self.timeout)
        elif type(self.loop) is multiprocessing.Process:
            self.loop.terminate()
        else:
            raise ValueError(f"Unknown type for input loop: {type(self.loop)}")

    def is_stopped(self):
        return self.stopped.is_set()


import os

def get_methods(method_type):
    file_folder = '/'.join(__file__.split('/')[:-1])
    
    methods_dir = ''
    try:
        methods_dir = os.listdir(f'{file_folder}/../{method_type}_methods')
        assert methods_dir, f'{method_type} methods folder is empty'
    except Exception as e:
        print(f'Error reading {method_type} methods folder: {e}')
    
    methods = dict(zip(['.'.join(method.split('.')[:-1]) for method in methods_dir],
                            [f"{method_type}_methods."+'.'.join(method.split('.')[:-1]) for method in methods_dir]))

    return methods
