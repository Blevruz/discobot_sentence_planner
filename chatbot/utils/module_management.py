# chatbot/utils/module_management.py
import os
import importlib
import utils.config
import json

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


def unroll_meta_modules(config):
    """Unroll meta-modules from a config"""
    # Two types: IO and Module
    config_buffer = list()

    link_replacement = dict()

    module_file_pairs = dict()

    # First pass: open meta-modules and take note of links to be replaced
    for module in config:
        if type(module) is not dict:
            raise Exception(f"Module {module['name']} is not a dictionary")

        # Is it any sort of meta-module?
        if module['module'].split('.')[0] == 'meta':

            # Is it an IO module?
            if module['module'].split('.')[1] == 'io':
                # Does it have a "meta" attribute?
                if 'meta' in module:
                    if module['meta'] in link_replacement:
                        link_replacement[module['meta']]['R_OUT'].append(module['name'])
                        for link in module['links']:
                            link_replacement[module['meta']]['L_IN'].append(link)
                    else:
                        raise Exception(f"Meta IO module {module['name']} claims to belong to meta module {module['meta']}, but that meta module is not defined")
                    
            # Is it a meta-module?
            elif module['module'].split('.')[1] == 'module':
                # Outbound links are copied to `to_replace_with`
                if module['name'] in link_replacement:
                    raise Exception(f"Meta-module {module['name']} is already defined")
                else:
                    link_replacement[module['name']] = {'R_OUT': list(), 
                                                        'L_OUT': module['links'],
                                                        'R_IN': [module['name']],
                                                        'L_IN': list()}
                # Does it specify a config file?
                config_file = ''
                if 'config' in module:
                    config_file = module['config']
                elif 'config' in module['args']:
                    config_file = module['args']['config']
                else:
                    raise Exception(f"Meta-module {module['name']} does not specify a config file!")

                # Recursive import error
                if "meta" in module:
                    if module_file_pairs[module['meta']] == config_file:
                        raise Exception(f"Recursive import detected: meta-module {module['name']} imports itself")
                # Add to module file pairs
                module_file_pairs[module['name']] = config_file

                # Load file to buffer
                with open(config_file, 'r') as f:
                    temp_config_buffer = json.load(f)
                    for temp_module in temp_config_buffer:
                        # Append meta-module name to module name
                        temp_module['name'] = f"{module['name']}_{temp_module['name']}"
                        # And to those in the links
                        for link in temp_module['links']:
                            link['target_name'] = f"{module['name']}_{link['target_name']}"
                        # Set "meta" attribute to meta-module name
                        temp_module['meta'] = module['name']
                        # Append to config to process later
                        config.append(temp_module)
        else:
            # Not a meta-module, just copy it to the buffer
            config_buffer.append(module)
        
    # Second pass: replace links
    for module in config_buffer:
        meta = None if "meta" not in module else module['meta']

        for link in module['links']:
            # Pointing to a meta-module
            if link['target_name'] in link_replacement:
                for l in link_replacement[link['target_name']]['L_IN']:
                    # Keep same 'from_slot' from original link
                    # use replacement 'name', 'target_name', and 'to_slot'
                    l['name'] = f"{link['name']}_to_{l['target_name']}"
                    l['from_slot'] = link['from_slot']
                    module['links'].append(l)
                module['links'].remove(link)
                # Did we actually delete it from the module though
            # Otherwise, we have to be in a meta-module to do any substitution
            if meta:
                if link['target_name'] in link_replacement[meta]['R_OUT']:
                    for l in link_replacement[meta]['L_OUT']:
                        # Keep same 'from_slot' from original link
                        # use replacement 'name', 'target_name', and 'to_slot'
                        l['name'] = f"{link['name']}_to_{l['target_name']}"
                        l['from_slot'] = link['from_slot']
                        module['links'].append(l)
                module['links'].remove(link)

    return config_buffer


def load_modules_from_config(config):
    """Load modules from a json config"""
    # Config ought to be a dictionary from a json
    # TODO: ensure proper formatting
    # [{"name": <name>, 
    #   "module": <input|middle|output>.<module>, 
    #   "args": {},
    #   "links": [{}]
    #  }, ...]

    # Before we begin, process all meta-modules
    config = unroll_meta_modules(config)

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
        assert len(module['module'].split('.')) >= 2, f"Module {module['name']}'s module string must be a string of the form <input|middle|output>_modules.<module>, not {module['module']}"
        # Is the prefix "meta" ?
        #if module['module'].split('.')[0] == 'meta_modules':
                # Meta-Modules! 
                # Either "submodule", which requires a config file,
                # "input", or "output", which require being in a submodule,
                # and serve to define the input or output of the submodule
                # (they are replaced on load to directly connect external modules
                # to those within the submodule)



        # Does the module name match the prefix?
        assert module['module'].split('.')[0] in module_lists.keys(), f"Module {module['name']}'s module string must be a string of the form <input|middle|output>_modules.<module>, not {module['module']}"
        # Does the module name match the suffix?
        assert module['module'].split('.')[1] in module_lists[module['module'].split('.')[0]], f"Module {module['name']} attempts to load module {module['module'].split('.')[1]} which does not exist in {module['module'].split('.')[0]} modules"




