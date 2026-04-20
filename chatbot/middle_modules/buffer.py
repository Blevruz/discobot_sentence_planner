# chatbot/middle_modules/buffer.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot
import utils.config

buffer_behaviors = ["overwrite",    # Buffer overwrites oldest data if full
                    "stop",         # Buffer stops accepting data if full
                    "flush",        # Buffer sends data if full
                    ]

class Buffer(DummyMiddle):
    """Holds a fixed-size buffer of incoming data.
    Sends it forwards either when full, or on receiving a flush signal.
    Bypass can be toggled with the bypass input queue.
    """

    def action(self, i):
        try:
            if len(self._input_queues['bypass']) > 0:
                while not self._input_queues['bypass'].empty() :
                    self._input_queues['bypass'].get()
                    self.bypass = not self.bypass

            while not self.input_queue.empty():
                data = self.input_queue.get()
                if self.bypass:
                    self.output_queue.put(data)
                else:
                    self._buffer.append(data)
                    if len(self._buffer) >= self._buffer_size:
                        if self._buffer_behavior == "flush":
                            self._flush_buffer()
                        elif self._buffer_behavior == "overwrite":
                            self._buffer = self._buffer[-self._buffer_size:]
            if len(self._input_queues['flush']) > 0:
                flush = self._input_queues['flush'].get()
                if flush:
                    self._flush_buffer()
        except Exception as e:
            utils.config.debug_print(f"[{self.name}] Error: {e}")

    def _flush_buffer(self):
        utils.config.debug_print(f"[{self.name}] Flushing buffer...")
        if len(self._buffer) > 0:
            if self.datatype_out == "string":
                out_str = "".join(self._buffer)
                utils.config.debug_print(f"[{self.name}] ... as string: {out_str}")
                self.output_queue.put(out_str)
            elif self.datatype_out == "audio":
                utils.config.debug_print(f"[{self.name}] ... as audio")
                #TODO: AUdio as a set of bytes
                self.output_queue.put(self._buffer)
            else: 
                utils.config.debug_print(f"[{self.name}] ... as a list")
                self.output_queue.put(self._buffer)
            self._buffer = []
                    

    def __init__(self, name="buffer", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = args.get('datatype_in', "any")
        self.datatype_out = args.get('datatype_out', "any")

        self._input_queues['flush'] = QueueSlot(self, 'input', datatype='any')
        self._input_queues['bypass'] = QueueSlot(self, 'input', datatype='any')
        self.bypass = False
        self._buffer_size = args.get('buffer_size', 10)
        self._buffer_behavior = args.get('buffer_behavior', "flush")
        self._buffer = []

middle_modules_class['buffer'] = Buffer
