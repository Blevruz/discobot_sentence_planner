#!venv/bin/python
# chatbot/main.py
import argparse
import importlib
import time
from utils.module_management import get_modules, load_modules_from_config
import utils.config
from utils.config import load_config

def manual_module_specification(args, input_modules: str, middle_modules: list, output_modules: str) -> dict:
    """Specify what modules to use. 
    Expects one input, one output, and any number of middle modules
    """

    if utils.config.verbose:
        utils.config.debug_print(f" Input module: {args.input}")
        utils.config.debug_print(f" Middle modules: {args.middle}")
        utils.config.debug_print(f" Output module: {args.output}")

    loaded_modules = dict()
    output_module = importlib.import_module(output_modules[args.output])
    output_module = output_module.output_modules_class[args.output](args.output)

    middle_modules = [importlib.import_module(middle_modules[m]) for m in args.middle]
    middle_module_list = [mm.middle_modules_class[mn](mn) for mm, mn in zip(middle_modules, args.middle)]

    input_module = importlib.import_module(input_modules[args.input])
    input_module = input_module.input_modules_class[args.input](args.input)

    # module linking

    # Do we have any middle modules? If so, link input to the first one
    if len(middle_module_list) > 0:
        input_module.link_to(middle_module_list[0])
        # Link the rest of the middle modules together if there's more than one
        # left
        for i in range(len(middle_module_list) - 1):
            middle_module_list[i].link_to(middle_module_list[i + 1])
        # Link the last middle module to the output module
        middle_module_list[-1].link_to(output_module)
    else:
        input_module.link_to(output_module)

    if utils.config.verbose:
        utils.config.debug_print(" Input module: {input_module.name}, input module's output queue: {input_module.output_queue}")
        for m in middle_module_list:
            utils.config.debug_print(" Middle module: {m.name}, middle module's input queue: {m.input_queue}, middle module's output queue: {m.output_queue}")
        utils.config.debug_print(" Output module: {output_module.name}, output module's input queue: {output_module.input_queue}")

    loaded_modules[f"input_{input_module.name}"] = input_module
    for m in middle_module_list:
        loaded_modules[f"middle_{m.name}"] = m
    loaded_modules[f"output_{output_module.name}"] = output_module
    return loaded_modules


def main():
    input_modules = get_modules("input")
    output_modules = get_modules("output")
    middle_modules = get_modules("middle")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', dest='config',
        required=False,
        default=None,
        help=f"Configuration file for the chatbot")
    parser.add_argument(
        '--verbose', dest='verbose',
        action='store_true',
        help='Print debug information')
    parser.add_argument(
        '--input', dest='input',
        required=False,
        default='dummy',
        help=f"Input module for the chatbot. Use one of {input_modules.keys()}.")
    parser.add_argument(
        '--middle', dest='middle',
        nargs='*',
        required=False,
        default=[],
        help=f"Middle modules for the chatbot. Use entries from {middle_modules.keys()}.")
    parser.add_argument(
        '--output', dest='output',
        required=False,
        default='dummy',
        help=f"Output module for the chatbot. Use one of {output_modules.keys()}.")
    args = parser.parse_args()

    utils.config.verbose = args.verbose

    loaded_modules = None
    if args.config is None:
        loaded_modules = manual_module_specification(args, input_modules, middle_modules, output_modules)
    else:
        config = load_config(args.config)
        loaded_modules = load_modules_from_config(config)

    if utils.config.verbose:
        utils.config.debug_print(f"Loaded modules: {loaded_modules.keys()}")
        for m in loaded_modules.values():
            for i_qs, i_qs_key in zip(m.input_queues.values(), m.input_queues.keys()):
                utils.config.debug_print(f"Input slot {i_qs_key} of module {m.name} has {len(i_qs)} queues")
                if type(i_qs) is str:
                    continue
                for i_q in i_qs._queues:
                    utils.config.debug_print(f"Input queue {i_q.name} in slot {i_qs_key} of module {m.name} goes from {i_q.mod_from.name} to {i_q.mod_to.name}")
            for o_qs, o_qs_key in zip(m.output_queues.values(), list(m.output_queues.keys())):
                utils.config.debug_print(f"Output slot {o_qs_key} of module {m.name} has {len(o_qs)} queues")
                if type(o_qs) is str:
                    continue
                for o_q in o_qs:
                    utils.config.debug_print(f"Input queue {o_q.name} in slot {o_qs_key} of module {m.name} goes from {o_q.mod_from.name} to {o_q.mod_to.name}")

    if utils.config.verbose:
        utils.config.debug_print(" Starting loops")

    for m in loaded_modules.values():
        m.start_loop()

    # Idle infinitely while the loops are running. Wait for keyboard interrupt.
    while True:
        try:
            time.sleep(2.4)
        except KeyboardInterrupt:
            break

    for m in loaded_modules.values():
        m.stop_loop()

    if utils.config.verbose:
        utils.config.debug_print(" Done")


if __name__ == '__main__':
    main()
