# chatbot/middle_methods/dummy.py
from utils.module_management import DummyModule

class DummyMiddle(DummyModule):

    def action(self, i):
        return

    def __init__(self, name = "dummy_middle"):
        DummyModule.__init__(self, name)
        self.type = "middle"

middle_methods_class = dict()
middle_methods_class['dummy'] = DummyMiddle
