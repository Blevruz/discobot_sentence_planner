#chatbot/middle_modules/regexp_modifier.py

import re
from middle_modules.dummy import DummyMiddle, middle_modules_class

class RegexpModifier(DummyMiddle):
"""Applies a regexp to the input string and sends the modified string to the output queue.
"""
text

def action(self, i):
    text = self.input_queue.get()
    if text:
        modified_text = re.sub(self.regexp, self.replacement, text)
        self.output_queue.put(modified_text)

def __init__(self, name="regexp_modifier", **args):
    """Initializes the module.
    Arguments:
        regexp : str
            Regular expression to apply
        replacement : str
            String to replace matches with
    """

    super().__init__(name, **args)
    self._loop_type = 'process'
    self.datatype_in = 'string'
    self.datatype_out = 'string'
    self.regexp = args.get('regexp', '')
    self.replacement = args.get('replacement', '')

middle_modules_class['regexp_modifier'] = RegexpModifier
