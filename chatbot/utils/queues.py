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
        utils.config.debug_print(f"Binding {self.name} from {from_module.name}")
        from_module.add_output_queue(self, slot)


    @property
    def mod_to(self):
        return self._mod_to

    def bind_to(self, to_module, slot="default"):
        """Assigns this queue as an input queue for the given module"""
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

    def _join_thread_with_timeout(queue, timeout):
        """Join a multiprocessing.Queue's internal feeder thread, but don't
        block forever if it's stuck (e.g. after a killed process left its
        write lock held)."""
        done = threading.Event()
    
        def _joiner():
            try:
                queue.join_thread()
            except Exception:
                pass
            finally:
                done.set()
    
        t = threading.Thread(target=_joiner, daemon=True)
        t.start()
        finished = done.wait(timeout)
        return finished  # False means it timed out / is still hung


    def _drain_queue(self, force=False):
        """Drain the queue. If force=True, we know the writing process was
        killed and may have left the queue in a bad state, so we skip the
        clean join and just cancel it."""
        q = self._queue
        try:
            while True:
                q.get_nowait()
        except Exception:
            pass
    
        if isinstance(q, multiprocessing.queues.Queue):
            if force:
                # Don't try to cleanly flush a queue whose writer was killed;
                # the feeder thread's lock may be stuck forever.
                try:
                    q.cancel_join_thread()
                    q.close()
                except Exception:
                    pass
            else:
                try:
                    q.close()
                    if not self._join_thread_with_timeout(q, timeout=2):
                        utils.config.debug_print(
                            f"Queue {self.name} join_thread() timed out, "
                            f"cancelling instead")
                        q.cancel_join_thread()
                except Exception:
                    pass



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
        self._offset_get = 0

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

    def put(self, data):
        if self._direction == 'input':
            raise ValueError(f"Attempting to put data in input queue slot")
        else:
            # Each queue in the slot gets the data
            for queue in self._queues:
                queue.put(data)

    def get(self):
        """ Get data from one of the queues in this slot."""
        if self._direction == 'output':
            raise ValueError(f"Attempting to get data from output queue slot")
        else:
            # TODO: Try to order received input chronologically somehow
            # In the meantime we'll just get the first non-empty queue and
            # change the offset to not always get the same queue
            for qi in range(len(self._queues)):
                queue = self._queues[(self._offset_get + qi) % len(self._queues)]
                if not queue.empty():
                    self._offset_get = (self._offset_get + qi + 1) % len(self._queues)
                    return queue.get()

        return None

    def empty(self):
        for queue in self._queues:
            if not queue.empty():
                return False
        return True
    
    def full(self):
        # Bit harder than empty since it's probably also interesting to know
        # if we have a single full queue in there
        # So let's yell at the user not to use this I guess!
        raise NotImplementedError("QueueSlot.full() is not implemented right now")
        #for queue in self._queues:
        #    if not queue.full():
        #        return False
        #return True




        """Put data in the queue slot"""

    def add_queue(self, queue):
        """Add a queue to this queue slot"""
        if self._datatype == "any" or queue.datatype == "any" \
                or self._datatype == queue.datatype:
            if len(self._queues) < self._size or self._size == -1:
                self._queues.append(queue)
                if self._direction == 'input':
                    queue._mod_to = self._module
                    utils.config.debug_print(f"Setting {self._module.name} to {queue.name}'s mod_to: {queue._mod_to.name}")
                elif self._direction == 'output':
                    queue._mod_from = self._module
                    utils.config.debug_print(f"Setting {self._module.name} to {queue.name}'s mod_from: {queue._mod_from.name}")

            else:
                raise ValueError(f"Queue slot is full, cannot add queue {queue.name}")
        else:
            raise ValueError(f"Datatype mismatch between queue and queue slot, with datatypes {self.datatype} and {queue.datatype}")
        utils.config.debug_print(f"Queue slot {self._direction} of {self._module.name} now has {len(self._queues)} queues")

    def remove_queue(self, queue):
        """Remove a queue from this queue slot"""
        if queue in self._queues:
            self._queues.remove(queue)

