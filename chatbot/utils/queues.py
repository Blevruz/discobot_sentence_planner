# chatbot/utils/queues.py
import multiprocessing
import utils.config
from queue import Empty


def datatype_match(datatype1, datatype2):
    """Check if two datatypes match"""
    if datatype1 == datatype2:
        return True
    if datatype1 == "any" or datatype2 == "any":
        return True
    return False

class QueueWrapper:
    """Wrapper for the unidirection queues used between modules"""

    def __init__(self, datatype="string", name="unnamed_queue"): 
        """Creates a new queue wrapper
        Arguments:
            datatype: datatype of the queue
            name: name of the queue
        """
        self.name = name
        self.datatype = datatype
        self._queue = multiprocessing.Queue()
        self._mod_from = None
        self._mod_to = None

    @property
    def mod_from(self):
        return self._mod_from

    def bind_from(self, from_module, slot="default"):
        """Assigns this queue as an output queue for the given module"""
        if utils.config.verbose:
            utils.config.debug_print(f"Binding {self.name} from {from_module.name}")
        from_module.add_output_queue(self, slot)


    @property
    def mod_to(self):
        return self._mod_to

    def bind_to(self, to_module, slot="default"):
        """Assigns this queue as an input queue for the given module"""
        if utils.config.verbose:
            utils.config.debug_print(f"Binding {self.name} to {to_module.name}")
        to_module.add_input_queue(self, slot)


    def get(self):
        """Get an item from the queue"""
        try:
            if self._mod_from is not None:
                return self._queue.get_nowait()
            else:
                raise ValueError(f"No input module linked to this queue: {self.name}, {self._mod_from} -> {self._mod_to}")
        except Empty:
            return None

    def put(self, item):
        """Put an item in the queue"""
        if self._mod_to is not None:
            self._queue.put(item)
        else:
            raise ValueError(f"No output module linked to this queue: {self.name}, {self._mod_from.name} -> {self._mod_to}")

    def empty(self):
        """Check if the queue is empty"""
        return self._queue.empty()

    def full(self):
        """Check if the queue is full"""
        return self._queue.full()

class QueueSlot:
    """Manages the variable number of queues that can be linked to a module's
    input or output."""
    def __init__(self, module, direction, datatype="any", name="", size=-1):
        """
        Arguments:
            module: module that owns this queue slot
            direction: direction of the queue slot (input or output)
            datatype: datatype of the queue slot
            size: maximum number of queues that can be linked to this slot
        """
        self._module = module
        self._direction = direction
        assert direction in ['input', 'output'], f"Direction must be 'input' or 'output', not {direction}"
        self._datatype = datatype
        self._size = size
        self._queues = []

    @property
    def datatype(self):
        return self._datatype
    @datatype.setter
    def datatype(self, datatype):
        # TODO: have a datatype checker
        self._datatype = datatype

    def __getitem__(self, key):
        return self._queues[key]

    def __len__(self):
        return len(self._queues)

    def add_queue(self, queue):
        """Add a queue to this queue slot"""
        if self._datatype == "any" or queue.datatype == "any" \
                or self._datatype == queue.datatype:
            if len(self._queues) < self._size or self._size == -1:
                self._queues.append(queue)
                if self._direction == 'input':
                    queue._mod_to = self._module
                    if utils.config.verbose:
                        utils.config.debug_print(f"Setting {self._module.name} to {queue.name}'s mod_to: {queue._mod_to.name}")
                elif self._direction == 'output':
                    queue._mod_from = self._module
                    if utils.config.verbose:
                        utils.config.debug_print(f"Setting {self._module.name} to {queue.name}'s mod_from: {queue._mod_from.name}")

            else:
                raise ValueError(f"Queue slot is full, cannot add queue {queue.name}")
        else:
            raise ValueError(f"Datatype mismatch between queue and queue slot, with datatypes {self.datatype} and {queue.datatype}")
        if utils.config.verbose:
            utils.config.debug_print(f"Queue slot {self._direction} of {self._module.name} now has {len(self._queues)} queues")

    def remove_queue(self, queue):
        """Remove a queue from this queue slot"""
        if queue in self._queues:
            self._queues.remove(queue)


