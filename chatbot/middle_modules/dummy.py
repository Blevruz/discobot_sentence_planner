# chatbot/middle_modules/dummy.py
from utils.dummy_module import DummyModule

class DummyMiddle(DummyModule):
    """Dummy middle module. Probably shouldn't be used in anything.
    Other middle modules should inherit from this."""

    def action(self, i):
        """No action"""
        return

    def __init__(self, name = "dummy_middle", **args):
        DummyModule.__init__(self, name, **args)
        self.type = "middle"

middle_modules_class = dict()
middle_modules_class['dummy'] = DummyMiddle
