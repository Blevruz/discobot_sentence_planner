# chatbot/middle_modules/queue_concat.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueWrapper, QueueSlot
import utils.config

class QueueConcat(DummyMiddle):

    def action(self, i):
        for k, v in zip(self._input_queues.keys(), self._input_queues.values()):
            for q in v:
                while not q.empty():
                    self.wip_text = self.wip_text.replace(f"{{{k}}}", q.get())

        if not self.input_queue.empty():
            if utils.config.verbose:
                utils.config.debug_print(f"QueueConcat: {self.wip_text}")
            self.output_queue.put(self.wip_text)
            self.wip_text = self.format

    def __init__(self, name="queue_concat", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'thread'
        del self._input_queues['input']
        self._input_queues['trigger'] = QueueSlot(self, 'input', datatype='any')
        self._input_queues['default'] = self._input_queues['trigger']
        self.input_queue_names = args.get('input_queues', ['input'])
        self.format = args.get('format', "{"+"} {".join(self.input_queues)+"}")
        self.wip_text = self.format

        for i in self.input_queue_names:
            self._input_queues[i] = QueueSlot(self, 'input', datatype='string')


middle_modules_class['queue_concat'] = QueueConcat
