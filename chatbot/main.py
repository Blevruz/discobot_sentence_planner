#!/usr/bin/env python
# CONDITIONAL IMPORT WARNING!
# We import stuff depending on arguments
import argparse
import importlib
import time
from utils.module_management import get_methods

if __name__ == '__main__':

    input_methods = get_methods("input")
    output_methods = get_methods("output")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--verbose', dest='verbose',
        action='store_true',
        help='Print debug information')
    parser.add_argument(
        '--input', dest='input',
        required=False,
        default='dummy',
        help=f"Input method for the chatbot. Use one of {input_methods.keys()}")
    parser.add_argument(
        '--output', dest='output',
        required=False,
        default='dummy',
        help=f"Output method for the chatbot. Use one of {output_methods.keys()}")
    args = parser.parse_args()

    verbose = args.verbose
    if verbose:
        print(f"[DEBUG] Input method: {args.input}")
        print(f"[DEBUG] Output method: {args.output}")

    output_module = importlib.import_module(output_methods[args.output])
    output_method = output_module.output_methods_class[args.output](args.output)
    output_method.start_loop(verbose)

    input_module = importlib.import_module(input_methods[args.input])
    input_method = input_module.input_methods_class[args.input](args.input)
    input_method.start_loop(verbose)

    input_method.link_to(output_method)

    timestart = time.time()
    while time.time() - timestart < 10:
        time.sleep(2.4)
    input_method.stop_loop(verbose)
    output_method.stop_loop(verbose)
    
    if verbose:
        print(f"[DEBUG] Done")
