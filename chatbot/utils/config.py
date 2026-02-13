# chatbot/utils/config.py
import json

# stolen wholesale from https://stackoverflow.com/questions/34115298/how-do-i-get-the-current-depth-of-the-python-interpreter-stack
from itertools import count
import sys
import os

def stack_size2a(size=2):
    """Get stack size for caller's frame.
    """
    frame = sys._getframe(size)

    for size in count(size):
        frame = frame.f_back
        if not frame:
            return size

def debug_spaces():
    """Return a string of spaces equal to the depth of the call stack
    """
    return " " * stack_size2a(3)

def debug_print(*args, **kwargs):
    """fancy print for debugging"""
    print("[DEBUG]"+debug_spaces(), *args, **kwargs)

verbose = False

def load_config(filename):
    """Load a JSON config file"""
    with open(filename, 'r') as f:
        return json.load(f)

def process_config_args(args : dict):
    """Process arguments from a config file
        - If arg value begins with '$', it's an environment variable
        - If arg value begins with '@', it's a file
    """
    for key, value in args.items():
        if isinstance(value, str):
            if value.startswith('$'):
                args[key] = os.environ[value[1:]]
                # Shouldn't crash if empty but we should say something about it
                if verbose:
                    if not args[key]:
                        debug_print(f"Environment variable {value[1:]} is empty")
            elif value.startswith('@'):
                # If it's a json file, load it as a json
                if value.endswith('.json'):
                    with open(value[1:], 'r') as f:
                        args[key] = json.load(f)
                # Else, assume it's a text file, load it as a string
                else:
                        with open(value[1:], 'r') as f:
                            args[key] = f.read()

