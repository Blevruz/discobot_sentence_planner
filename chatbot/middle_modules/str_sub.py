# chatbot/middle_modules/str_sub.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.config
import random

class StrSub(DummyMiddle):
    """Replaces character sequences in a string based on a pre-defined
    dictionary.
    """

    def action(self, i):
        self.wip_text = self.input_queue.get()
        if self.wip_text:
            for k, v in self.subs.items():
                if type(v) == list:
                    v = random.choice(v)
                    self.wip_text = self.wip_text.replace(k, v)
                self.wip_text = self.wip_text.replace(k, v)
            if utils.config.verbose:
                utils.config.debug_print(f"[{self.name}]StrSub: {self.wip_text}")
            self.output_queue.put(self.wip_text)

    def __init__(self, name="str_sub", **args):
        """Initializes the module.
        Arguments:
            input_queues : list
                List of input queues to be created
            sub_file : json
                File containing the substitution dictionary
            subs : dict
                Dictionary of character sequences to be replaced,
                used if sub_file is not provided
            seed : int
                Seed for random number generator
        """
        super().__init__(name, **args)
        self.subs = args.get("subs", {})
        self.sub_file = args.get("sub_file", None)
        if self.sub_file:
            with open(self.sub_file, "r") as f:
                self.subs = json.load(f)
        self.wip_text = ""
        self.seed = args.get("seed", None)
        if self.seed:
            random.seed(self.seed)
            




