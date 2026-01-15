# chatbot/utils/dummy_module.py
import multiprocessing
import threading
import utils.config
from utils.queues import QueueWrapper, QueueSlot


class DummyModule:
    def __init__(self, name = "dummy", **args):
        self._type = 'dummy'
        self._name = name
        # Set of queues we only read from
        self._input_queues = dict()
        self._input_queues['input'] = QueueSlot(self, \
                'input', datatype='any')
        self._input_queues['default'] = self._input_queues['input']
        # Set of queues we only write to
        self._output_queues = dict()
        self._output_queues['output'] = QueueSlot(self, \
                'output', datatype='any')
        self._output_queues['default'] = self._output_queues['output']
        self._loop_type = 'blocking'
        self._loop_timeout = 1

        if utils.config.verbose:
            print("[DEBUG] Module {name} initializing with args: {args}")


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
    def loop_type(self):
        return self._loop_type
    
    # Useful shortcuts to input/output queues
    # Might be worth gutting for concision/good practices
    @property
    def input_queue(self):
        return self._input_queues['default'][0]
    @property
    def datatype_in(self):
        return self._input_queues['default'].datatype
    @datatype_in.setter
    def datatype_in(self, datatype):
        self._input_queues['default'].datatype = datatype

    @property
    def output_queue(self):
        return self._output_queues['default'][0]
    @property
    def datatype_out(self):
        return self._output_queues['default'].datatype
    @datatype_out.setter
    def datatype_out(self, datatype):
        self._output_queues['default'].datatype = datatype

    def _create_input_queue(self, slot="default", name="input_queue"): 
        if utils.config.verbose:
            print(f"[DEBUG] Creating input queue {name} for {self.name}",\
                    f"slot {slot}")
        queue = QueueWrapper(datatype=self._input_queues[slot].datatype, \
                name=name)
        self._input_queues[slot].add_queue(queue)
        return queue

    def _create_output_queue(self, slot="default", name="output_queue"): 
        if utils.config.verbose:
            print(f"[DEBUG] Creating output queue {name} for {self.name}",\
                    f"slot {slot}")
        queue = QueueWrapper(datatype=self._output_queues[slot].datatype, \
                name=name)
        self._output_queues[slot].add_queue(queue)
        return queue

    def add_input_queue(self, queue, slot="default"):
        self._input_queues[slot].add_queue(queue)

    def add_output_queue(self, queue, slot="default"):
        self._output_queues[slot].add_queue(queue)

    def link_to(self, other, from_slot="default", to_slot="default", name=None):
        if utils.config.verbose:
            print(f"[DEBUG] Setting {self.name}'s output queue as", \
                    f"{other.name}'s input queue,", \
                    f"of types {self._output_queues[from_slot].datatype}",\
                    f"and {other._input_queues[to_slot].datatype}")
        if name is None:
            name = f"{self.name}_to_{other.name}_queue"
        new_queue = self._create_output_queue(slot=from_slot,\
                name=name)
        new_queue.bind_to(other, slot=to_slot)

    def link_from(self, other, from_slot="default", to_slot="default", name=None):
        if utils.config.verbose:
            print(f"[DEBUG] Setting {self.name}'s input queue as", \
                    f"{other.name}'s output queue,", \
                    f"of types {self._input_queues[to_slot].datatype}",\
                    f"and {other._output_queues[from_slot].datatype}")
        if name is None:
            name = f"{other.name}_to_{self.name}_queue"
        new_queue = self._create_input_queue(slot=to_slot,\
                name=name)
        new_queue.bind_from(other, slot=from_slot)

    def _loop(self):
        i = 0
        while not self.is_stopped():
            self.action(i)
            i += 1

    # Overwrite this module if you want to do something when the loop starts
    def module_start(self):
        if utils.config.verbose:
            print(f"[DEBUG] Called empty module_start() for {self.name}")

    def start_loop(self):
        if utils.config.verbose:
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

    # Overwrite this module if you want to do something when the loop ends
    def module_stop(self):
        if utils.config.verbose:
            print(f"[DEBUG] Called empty module_stop() for {self.name}")

    def stop_loop(self):
        if utils.config.verbose:
            print(f"[DEBUG] Stopping {self.type} loop for {self.name}")
        self.stopped.set()
        if self._loop_type == 'thread':
            self.loop.join(self._loop_timeout)
        elif self._loop_type == 'process':
            self.loop.terminate()
        self.module_stop()

    def is_stopped(self):
        return self.stopped.is_set()


