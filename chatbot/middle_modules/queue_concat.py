# chatbot/middle_modules/queue_concat.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueWrapper, QueueSlot
import utils.config

class QueueConcat(DummyMiddle):
    """Concatenates multiple input queues into a single output queue following
    a pre-defined, fstring-like format.
    String input to be concatenated go to the user-defined queues.
    The generated string is only output on receiving any input in the trigger
    queue.
    """

    def action(self, i):
        for k, v in zip(self._input_queues.keys(), self._input_queues.values()):
            for q in v:
                while not q.empty():
                    self.buffer[k] = q.get()

        if not self.input_queue.empty():
            for k, v in zip(self.buffer.keys(), self.buffer.values()):
                self.wip_text = self.wip_text.replace(f"{{{k}}}", v)
            if utils.config.verbose:
                utils.config.debug_print(f"QueueConcat: {self.wip_text}")
            self.output_queue.put(self.wip_text)
            self.buffer = {}
            self.wip_text = self.format

    def __init__(self, name="queue_concat", **args):
        """Initializes the module.
        Arguments:
            input_queues : list
                List of input queues to be created
            format : str
                Format string to use for concatenation
        """
            

        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'thread'
        del self._input_queues['input']
        self._input_queues['trigger'] = QueueSlot(self, 'input', datatype='any')
        self._input_queues['default'] = self._input_queues['trigger']
        self.input_queue_names = args.get('input_queues', ['input'])
        self.format = args.get('format', "{"+"} {".join(self.input_queues)+"}")
        self.wip_text = self.format
        self.buffer = {}

        for i in self.input_queue_names:
            if i == "trigger":
                raise ValueError("Queue \"trigger\" cannot be used as a",\
                    "concatenation string queue.")
            self._input_queues[i] = QueueSlot(self, 'input', datatype='string')


middle_modules_class['queue_concat'] = QueueConcat
