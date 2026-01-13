# chatbot/utils/module_management.py
import os

def get_modules(module_type):
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


"""
def load_modules_from_config(config):
    # Config ought to be a dictionary from a json
    # TODO: ensure proper formatting
    # [{"name": <name>, 
    #   "module": <input|middle|output>.<module>, 
    #   "args": {},
    #   "links": [{]
    #  }, ...]
    for module in config:
"""


