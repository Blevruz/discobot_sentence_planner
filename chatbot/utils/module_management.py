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
    #   "links": [{}]
    #  }, ...]
    # TODO: meta-module
    # [{"name": <name>,
    #   "module": meta.[path],
    #   "args": {},
    #   "links": [{}]
    #  }, ...]

    input_modules = get_modules("input")
    output_modules = get_modules("output")
    middle_modules = get_modules("middle")

    loaded_modules = dict()
    loaded_config = list()
    module_libs = dict()
    # First pass: load every module
    for module in config:
        # If the module is a string, we want to process it same as config args
        if type(module) is str:
            utils.config.debug_print(f"Processing string \"{module}\"...")
            config.append(utils.config.process_config_arg(module))
            utils.config.debug_print(f"...into {module}")
            continue

        # If the module is a list, move all its content to the main list
        if type(module) is list:
            utils.config.debug_print(f"Popping list...")
            for m in module:
                utils.config.debug_print(f"Appending {m} to config")
                config.append(m)
            continue

        # Otherwise, the module should be a dictionary
        if type(module) is not dict:
            raise Exception(f"Module {module['name']} is not a dictionary")

        mod_split = module['module'].split('.')
        mod_lib = module['module']
        class_list = None

        # Load module library if it isn't already loaded
        if mod_lib not in module_libs:
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
        utils.config.debug_print(f"Loading module {module['name']} from {mod_lib}")

        if module['name'] in loaded_modules:
            raise Exception(f"Module with name {module['name']} already loaded")

        # Add module's config to loaded config
        loaded_config.append(module)

        # Process arguments
        utils.config.process_config_args(module['args'])

        # Add module to loaded modules
        loaded_modules[module['name']] = class_list[mod_split[1]]( \
                module['name'], \
                **module['args'])

    # Second pass: link modules
    for module in loaded_config:
        utils.config.debug_print(f"Linking module {module}")
        for link in module['links']:
            if link['target_name'] not in loaded_modules:
                raise Exception(f"Module {link['target_name']} not loaded")
            loaded_modules[module['name']].link_to( \
                    loaded_modules[link['target_name']], \
                    from_slot=link['from_slot'], \
                    to_slot=link['to_slot'], \
                    name=link['name'])
    
    return loaded_modules


def check_config(config):
    """Check that a config file conforms to the format
        - List of dictionaries representing modules
        - Each dictionary has a name, module, args and links
        - args and links are optional
        - links is a list of dictionaries
        - args is a dictionary
        - Each dictionary's name is unique
        - Each dictionary's module is a string of the form 
        <input|middle|output>_modules.<module>
        - Each module must match a module in the appropriate folder
        - Each dictionary's args is a dictionary
    """
    assert isinstance(config, list), "Config must be a list"
    names = []
    module_lists = dict()
    module_lists["input_modules"] = get_modules("input")
    module_lists["output_modules"] = get_modules("output")
    module_lists["middle_modules"] = get_modules("middle")
    for module in config:
        assert isinstance(module, dict), "Module must be a dictionary"
        assert 'name' in module, "Module must have a name"
        assert isinstance(module['name'], str), "Module name must be a string"
        assert 'module' in module, "Module must have a module identifier string"
        assert isinstance(module['module'], str), "Module must be a string"
        if module['name'] in names:
            raise Exception(f"Module with name {module['name']} already exists")
        names.append(module['name'])
        # Does the module name fit the [prefix, suffix] format?
        assert len(module['module'].split('.')) == 2, f"Module {module['name']}'s module string must be a string of the form <input|middle|output>_modules.<module>, not {module['module']}"
        # Does the module name match the prefix?
        assert module['module'].split('.')[0] in module_lists.keys(), f"Module {module['name']}'s module string must be a string of the form <input|middle|output>_modules.<module>, not {module['module']}"
        # Does the module name match the suffix?
        assert module['module'].split('.')[1] in module_lists[module['module'].split('.')[0]], f"Module {module['name']} attempts to load module {module['module'].split('.')[1]} which does not exist in {module['module'].split('.')[0]} modules"




