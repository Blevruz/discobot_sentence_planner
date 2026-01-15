# chatbot/middle_modules/dummy.py
from utils.dummy_module import DummyModule

class DummyMiddle(DummyModule):

    def action(self, i):
        return

    def __init__(self, name = "dummy_middle", **args):
        DummyModule.__init__(self, name, **args)
        self.type = "middle"

middle_modules_class = dict()
middle_modules_class['dummy'] = DummyMiddle
