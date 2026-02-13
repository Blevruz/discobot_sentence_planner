# chatbot/utils/module_management.py
import os
import importlib
import utils.config

def get_modules(module_type):
    """Get a list of modules of a given type within the adequate folder"""
    file_folder = '/'.join(__file__.split('/')[:-1])
    
    modules_dir = ''
    try:
        modules_dir = os.listdir(f'{file_folder}/../{module_type}_modules')
        assert modules_dir, f'{module_type} modules folder is empty'
    except Exception as e:
        print(f'Error reading {module_type} modules folder: {e}')
    
    modules = dict(zip(['.'.join(module.split('.')[:-1]) for module in modules_dir],
                            [f"{module_type}_modules."+'.'.join(module.split('.')[:-1]) for module in modules_dir]))

    return modules


def load_modules_from_config(config):
    """Load modules from a json config"""
    # Config ought to be a dictionary from a json
    # TODO: ensure proper formatting
    # [{"name": <name>, 
    #   "module": <input|middle|output>.<module>, 
    #   "args": {},
    #   "links": [{]
    #  }, ...]

    input_modules = get_modules("input")
    output_modules = get_modules("output")
    middle_modules = get_modules("middle")

    loaded_modules = dict()
    module_libs = dict()
    # First pass: load every module
    for module in config:
        mod_split = module['module'].split('.')
        mod_lib = module['module']
        class_list = None
        # Load module library if it isn't already loaded
        if mod_lib not in module_libs:
            if utils.config.verbose:
                utils.config.debug_print(f"Loading module library {mod_lib}")
            if mod_split[0] == 'input_modules':
                module_libs[mod_lib] = importlib.import_module( \
                        input_modules[mod_split[1]])
                class_list = module_libs[mod_lib].input_modules_class
            elif mod_split[0] == 'middle_modules':
                module_libs[mod_lib] = importlib.import_module( \
                        middle_modules[mod_split[1]])
                class_list = module_libs[mod_lib].middle_modules_class
            elif mod_split[0] == 'output_modules':
                module_libs[mod_lib] = importlib.import_module( \
                        output_modules[mod_split[1]])
                class_list = module_libs[mod_lib].output_modules_class
            else:
                raise Exception(f"{module['name']} from ({mod_lib})"+\
                        " is not an input, middle or output module")
        else:
            if mod_split[0] == 'input_modules':
                class_list = module_libs[mod_lib].input_modules_class
            elif mod_split[0] == 'middle_modules':
                class_list = module_libs[mod_lib].middle_modules_class
            elif mod_split[0] == 'output_modules':
                class_list = module_libs[mod_lib].output_modules_class
        if utils.config.verbose:
            utils.config.debug_print(f"Loading module {module['name']} from {mod_lib}")

        if module['name'] in loaded_modules:
            raise Exception(f"Module with name {module['name']} already loaded")

        # Process arguments
        utils.config.process_config_args(module['args'])

        # Add module to loaded modules
        loaded_modules[module['name']] = class_list[mod_split[1]]( \
                module['name'], \
                **module['args'])

    # Second pass: link modules
    for module in config:
        for link in module['links']:
            if link['target_name'] not in loaded_modules:
                raise Exception(f"Module {link['target_name']} not loaded")
            loaded_modules[module['name']].link_to( \
                    loaded_modules[link['target_name']], \
                    from_slot=link['from_slot'], \
                    to_slot=link['to_slot'], \
                    name=link['name'])
    
    return loaded_modules






