# chatbot/input_modules/http.py
from input_modules.dummy import DummyInput, input_modules_class
from utils.http_server import get_server, start_server, stop_server
import utils.config
import sys
import requests
import json

class HttpInput(DummyInput):
    """Input from http POST requests"""

    def module_post(self, handler, data):
        """Handle a POST request,
        send the received data to the output queue
        """
        length = int(handler.headers.get("Content-Length", 0))
        if length == 0:
            handler.send_error(400)
            return
        if self.convert_output == "json":
            data = json.loads(data)
        elif self.convert_output == "string":
            data = str(data)
        self.output_queue.put(data)
        body = self.default_response
        handler.send_response(200)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()

    def action(self, i):
        """All work done in the module_post function."""
        raise NotImplementedError("http input does not have an action module. It is a blocking module.")


    def __init__(self, name="http_input", **args):
        """Initializes the module. 
        Parameters:
        - port: Port to listen on. Default 8080
        - path: Path for this specific module to listen on. Default "/"
        """
        super().__init__(name, **args)
        self._loop_type = "blocking"
        self.datatype_out = "any"

        self.port = args.get("port", 8080)
        self.path = args.get("path", "in")
        self.convert_output = args.get("convert_output", "no") # One of "no", "json", "string"

        self.default_response = args.get("default_response", "ok")

        self.service_name = args.get("service_name", "input")
        self.server = get_server("0.0.0.0", self.port, modules_post = {self.path: self.module_post})

    def module_start(self):
        """Starts the server"""
        utils.config.debug_print(f"[{self.name}] Starting HttpInput loop on port {self.port}")
        self.server["post_handlers"][self.path] = lambda s, d: self.module_post(s, d)
        start_server("0.0.0.0", self.port)
        utils.config.debug_print(f"[{self.name}] HttpInput loop for {self.name} started on port {self.port}")

    def module_stop(self):
        """Stops the server"""
        utils.config.debug_print(f"[{self.name}] Stopping HttpInput loop on port {self.port}")
        stop_server("0.0.0.0", self.port)
        utils.config.debug_print(f"[{self.name}] HttpInput loop for {self.name} stopped on port {self.port}")

input_modules_class['http'] = HttpInput
