# chatbot/utils/config.py
import json

# stolen wholesale from https://stackoverflow.com/questions/34115298/how-do-i-get-the-current-depth-of-the-python-interpreter-stack
from itertools import count
import sys

def stack_size2a(size=2):
    """Get stack size for caller's frame.
    """
    frame = sys._getframe(size)

    for size in count(size):
        frame = frame.f_back
        if not frame:
            return size

def debug_spaces():
    return " " * stack_size2a(3)

def debug_print(*args, **kwargs):
    print("[DEBUG]"+debug_spaces(), *args, **kwargs)

verbose = False

def load_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)


