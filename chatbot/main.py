#!venv/bin/python
# chatbot/main.py
import argparse
import importlib
import time
from utils.module_management import get_methods
from utils.config import load_config, verbose

if __name__ == '__main__':

    input_methods = get_methods("input")
    output_methods = get_methods("output")
    middle_methods = get_methods("middle")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', dest='config',
        required=False,
        default='config.json',
        help=f"Configuration file for the chatbot")
    parser.add_argument(
        '--verbose', dest='verbose',
        action='store_true',
        help='Print debug information')
    parser.add_argument(
        '--input', dest='input',
        required=False,
        default='dummy',
        help=f"Input method for the chatbot. Use one of {input_methods.keys()}.")
    parser.add_argument(
        '--middle', dest='middle',
        nargs='*',
        required=False,
        default=[],
        help=f"Middle methods for the chatbot. Use entries from {middle_methods.keys()}.")
    parser.add_argument(
        '--output', dest='output',
        required=False,
        default='dummy',
        help=f"Output method for the chatbot. Use one of {output_methods.keys()}.")
    args = parser.parse_args()

    verbose = args.verbose
    if verbose:
        print(f"[DEBUG] Input method: {args.input}")
        print(f"[DEBUG] Middle methods: {args.middle}")
        print(f"[DEBUG] Output method: {args.output}")

    output_module = importlib.import_module(output_methods[args.output])
    output_method = output_module.output_methods_class[args.output](args.output)

    middle_modules = [importlib.import_module(middle_methods[m]) for m in args.middle]
    middle_method_list = [mm.middle_methods_class[mn](mn) for mm, mn in zip(middle_modules, args.middle)]

    input_module = importlib.import_module(input_methods[args.input])
    input_method = input_module.input_methods_class[args.input](args.input)

    # Method linking

    # Do we have any middle methods? If so, link input to the first one
    if len(middle_method_list) > 0:
        input_method.link_to(middle_method_list[0])
        # Link the rest of the middle methods together if there's more than one
        # left
        for i in range(len(middle_method_list) - 1):
            middle_method_list[i].link_to(middle_method_list[i + 1])
        # Link the last middle method to the output method
        middle_method_list[-1].link_to(output_method)
    else:
        input_method.link_to(output_method)

    if verbose:
        print(f"[DEBUG] Input module: {input_method.name}, input module's output queue: {input_method.output_queue}")
        for m in middle_method_list:
            print(f"[DEBUG] Middle module: {m.name}, middle module's input queue: {m.input_queue}, middle module's output queue: {m.output_queue}")
        print(f"[DEBUG] Output module: {output_method.name}, output module's input queue: {output_method.input_queue}")

        print(f"[DEBUG] Starting loops")

    output_method.start_loop()
    for m in middle_method_list:
        m.start_loop()
    input_method.start_loop()

    timestart = time.time()

    # Idle infinitely while the loops are running. Wait for keyboard interrupt.
    while True:
        try:
            time.sleep(2.4)
        except KeyboardInterrupt:
            break


    input_method.stop_loop()
    output_method.stop_loop()
    
    if verbose:
        print(f"[DEBUG] Done")
