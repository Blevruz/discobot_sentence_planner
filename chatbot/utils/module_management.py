from multiprocessing import Queue

class DummyModule:
    def __init__(self, name):
        self.name = name
        self.input_queue = Queue()
        self.output_queue = Queue()

    def set_input_queue(self, queue):
        self.input_queue = queue

    def get_input_queue(self):
        return self.input_queue

    def set_output_queue(self, queue):
        self.output_queue = queue

    def get_output_queue(self):
        return self.output_queue

    def link_to(self, other):
        other.set_input_queue(self.output_queue)


import os

def get_methods(method_type):
    file_folder = '/'.join(__file__.split('/')[:-1])
    
    methods_dir = ''
    try:
        methods_dir = os.listdir(f'{file_folder}/../{method_type}_methods')
        assert methods_dir, f'{method_type} methods folder is empty'
    except Exception as e:
        print(f'Error reading {method_type} methods folder: {e}')
    
    methods = dict(zip(['.'.join(method.split('.')[:-1]) for method in methods_dir],
                            [f"{method_type}_methods."+'.'.join(method.split('.')[:-1]) for method in methods_dir]))

    return methods
