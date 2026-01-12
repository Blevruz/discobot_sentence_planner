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

class QueueWrapper:
    def __init__(self, datatype="string", name="unnamed_queue"):
        self.name = name
        self.type = datatype
        self._queue = multiprocessing.Queue()
        self._mod_from = None
        self._mod_to = None

    @property
    def mod_from(self):
        return self._mod_from
    @mod_from.setter
    def mod_from(self, from_module):
        if from_module.type == "output":
            raise ValueError("Cannot set input queue from output module")
        self._mod_from = from_module
        self._mod_from.add_output_queue(self)

    @property
    def mod_to(self):
        return self._mod_to
    @mod_to.setter
    def mod_to(self, to_module):
        if to_module.type == "input":
            raise ValueError("Cannot set output queue to input module")
        self._mod_to = to_module
        self._mod_to.add_input_queue(self)

    def get(self):
        if self._mod_from is not None:
            return self._queue.get()
        else:
            raise ValueError("No input module linked to this queue")

    def put(self, item):
        if self._mod_to is not None:
            self._queue.put(item)
        else:
            raise ValueError("No output module linked to this queue")

    def empty(self):
        return self._queue.empty()

    def full(self):
        return self._queue.full()





class DummyModule:
    def __init__(self, name = "dummy", verbose=False):
        self._type = 'dummy'
        self._name = name
        self.verbose = verbose
        self.loop_timeout = 0.1
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
        if len(self._input_queues) > 0:
            return self._input_queues[0]
        else:
            return None
    @input_queue.setter
    def input_queue(self, queue):
        self._input_queues[0] = queue

    @property
    def output_queue(self):
        if len(self._output_queues) > 0:
            return self._output_queues[0]
        else:
            return None
    @output_queue.setter
    def output_queue(self, queue):
        self._output_queues[0] = queue

    @property
    def loop_type(self):
        return self._loop_type
    @loop_type.setter
    def loop_type(self, loop_type):
        self._loop_type = loop_type

    def _create_input_queue(self): 
        # Example implementation, only one input queue
        if len(self._input_queues) > 0:
            self._input_queues[0] = QueueWrapper()
        else:
            self._input_queues.append(QueueWrapper())
        self._input_queues[0].mod_to = self
        if self.verbose:
            print(f"[DEBUG] Created input queue {self._input_queues[0]} for {self.name}")
        return self._input_queues[0]

    ## Should we only be able to create queues in one direction?
    #  If yes, delete this method
    def _create_output_queue(self): 
        # Example implementation, only one output queue
        if len(self._output_queues) > 0:
            self._output_queues[0] = QueueWrapper()
        else:
            self._output_queues.append(QueueWrapper())
        self._output_queues[0].mod_from = self
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
        #other.add_input_queue(self._create_output_queue())
        if self.output_queue is None:
            self._create_output_queue()
        self.output_queue.mod_to = other

    def link_from(self, other):
        if self.verbose:
            print(f"[DEBUG] Setting {self.name}'s input queue as {other.name}'s output queue, of types {type(self.input_queue)} and {type(other.output_queue)}")
        #other.add_output_queue(self._create_input_queue())
        if self.input_queue is None:
            self._create_input_queue()
        self.input_queue.mod_from = other


    def _loop(self):
        i = 0
        while not self.is_stopped():
            self.action(i)
            i += 1

    # Overwrite this method if you want to do something when the loop starts
    def module_start(self):
        if self.verbose:
            print(f"[DEBUG] Called empty module_start() for {self.name}")

    def start_loop(self):
        if self.verbose:
            print(f"[DEBUG] Starting {self.type} loop for {self.name}")
        self.module_start()
        self.stopped = threading.Event()
        if self._loop_type == 'blocking':
            return
        if self._loop_type == 'thread':
            self.loop = threading.Thread(target=self._loop)
        elif self._loop_type == 'process':
            self.loop = multiprocessing.Process(target=self._loop)
        self.loop.start()

    # Overwrite this method if you want to do something when the loop ends
    def module_stop(self):
        if self.verbose:
            print(f"[DEBUG] Called empty module_stop() for {self.name}")

    def stop_loop(self):
        if self.verbose:
            print(f"[DEBUG] Stopping {self.type} loop for {self.name}")
        self.stopped.set()
        if self._loop_type == 'thread':
            self.loop.join(self.loop_timeout)
        elif self._loop_type == 'process':
            self.loop.terminate()
        self.module_stop()

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
