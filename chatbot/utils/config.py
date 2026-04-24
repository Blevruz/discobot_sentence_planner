# chatbot/utils/config.py
import json

# stolen wholesale from https://stackoverflow.com/questions/34115298/how-do-i-get-the-current-depth-of-the-python-interpreter-stack
from itertools import count
import sys
import os
import time

verbose = False

log_file = ""

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

start_time = time.time()

def truncate_float(f, n=3):
    """Truncate a float to n decimal places"""
    return float(f"{f:.{n}f}")


def debug_print(*args, **kwargs):
    """fancy print for debugging"""
    if verbose:
        print(f"[DEBUG] {truncate_float(time.time()-start_time)}s\t"+debug_spaces(), *args, **kwargs)
    if log_file:
        with open(log_file, 'a') as f:
            print(f"[DEBUG] {truncate_float(time.time()-start_time)}s\t"+debug_spaces(), *args, file=f, **kwargs)

def load_config(filename):
    """Load a JSON config file"""
    with open(filename, 'r') as f:
        return json.load(f)

def process_config_args(args : dict):
    """Process arguments from a config file"""
    for key, value in args.items():
        args[key] = process_config_arg(value)

def process_config_arg(arg):
    """Process an argument from a config file
        - If arg value begins with '$', it's an environment variable
        - If arg value begins with '@', it's a file
       If all else fails, return the argument
    """
    while isinstance(arg, str):
        if arg.startswith('$'):
            arg = os.environ[arg[1:]]
            # Shouldn't crash if empty but we should say something about it
            if not arg:
                debug_print(f"Environment variable {value[1:]} is empty")
        elif arg.startswith('@'):
            # If it's a json file, load it as a json
            if arg.endswith('.json'):
                with open(arg[1:], 'r') as f:
                    arg = json.load(f)
            # Else, assume it's a text file, load it as a string
            else:
                with open(arg[1:], 'r') as f:
                    arg = f.read()
        else:
            # Just a string? Then return
            break
    return arg

def nice_config_print(config):
    if verbose:
        for module in config:
            debug_print(f"Module {module['name']}:")
            debug_print(f"\tModule: {module['module']}")
            if 'args' in module:
                debug_print(f"\tArgs:")
                for arg in module['args']:
                    debug_print(f"\t\t{arg}: {module['args'][arg]}")
            if 'config' in module:
                debug_print(f"\tConfig: {module['config']}")
                subconfig = load_config(module['config'])
                nice_config_print(subconfig)
            if 'links' in module:
                debug_print(f"\tLinks:")
                for link in module['links']:
                    debug_print(f"\t\t{link['name']}: {link['from_slot']} -> {link['to_slot']} on module {link['target_name']}")
