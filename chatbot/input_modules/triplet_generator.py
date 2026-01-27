# chatbot/input_modules/triplet_generator.py
from input_modules.dummy import DummyInput, input_modules_class
import utils.config
import time

class TripletGenerator(DummyInput):
    """Sends a predefined set of triplets to the output queue.
    """

    def action(self, i):
        time.sleep(self.delay)
        self.output_queue.put(self._triplets[i%len(self._triplets[0])])

    def __init__(self, name="triplet_generator", **args):
        """Initializes the module.
        Arguments:
            triplets : list
                Lists of entries to make triplets to send to the output queue
        """
        DummyInput.__init__(self, name, **args)
        self._loop_type = 'process'
        self.datatype_out = 'triplet'
        self._triplets = args.get('triplets', [["Foo", "Bar", "Baz"], 
                                               ["Qux", "Quux", "Quuz"],
                                               ["Qux", "Qarault", "Qarply"],
                                               ["Corge", "Grault", "Garply"]])
        self.delay = args.get('delay', 1)

input_modules_class['triplet_generator'] = TripletGenerator
