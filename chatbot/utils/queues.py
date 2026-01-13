# chatbot/utils/queues.py
import multiprocessing
import utils.config


def datatype_match(datatype1, datatype2):
    if datatype1 == datatype2:
        return True
    if datatype1 == "any" or datatype2 == "any":
        return True
    return False

class QueueWrapper:
    def __init__(self, datatype="string", name="unnamed_queue"): 
        self.name = name
        self.datatype = datatype
        self._queue = multiprocessing.Queue()
        self._mod_from = None
        self._mod_to = None

    @property
    def mod_from(self):
        return self._mod_from

    def bind_from(self, from_module, slot="default"):
        if utils.config.verbose:
            print(f"[DEBUG] Binding {self.name} from {from_module.name}")
        from_module.add_output_queue(self, slot)


    @property
    def mod_to(self):
        return self._mod_to

    def bind_to(self, to_module, slot="default"):
        if utils.config.verbose:
            print(f"[DEBUG] Binding {self.name} to {to_module.name}")
        to_module.add_input_queue(self, slot)


    def get(self):
        if self._mod_from is not None:
            return self._queue.get()
        else:
            raise ValueError(f"No input module linked to this queue: {self.name}, {self._mod_from} -> {self._mod_to}")

    def put(self, item):
        if self._mod_to is not None:
            self._queue.put(item)
        else:
            raise ValueError(f"No output module linked to this queue: {self.name}, {self._mod_from} -> {self._mod_to}")

    def empty(self):
        return self._queue.empty()

    def full(self):
        return self._queue.full()

class QueueSlot:
    def __init__(self, module, direction, datatype="any", size=-1):
        self._module = module
        self._direction = direction
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

    def add_queue(self, queue):
        if self._datatype == "any" or queue.datatype == "any" \
                or self._datatype == queue.datatype:
            if len(self._queues) < self._size or self._size == -1:
                self._queues.append(queue)
                if self._direction == 'input':
                    queue._mod_to = self._module
                elif self._direction == 'output':
                    queue._mod_from = self._module

            else:
                raise ValueError(f"Queue slot is full, cannot add queue {queue.name}")
        else:
            raise ValueError(f"Datatype mismatch between queue and queue slot, with datatypes {self.datatype} and {queue.datatype}")

    def remove_queue(self, queue):
        if queue in self._queues:
            self._queues.remove(queue)


