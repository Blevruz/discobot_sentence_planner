# chatbot/output_modules/http.py
from output_modules.dummy import DummyOutput, output_modules_class
from utils.http_server import get_server, start_server, stop_server
import json
import utils.config
import threading
import queue

class HttpOutput(DummyOutput):
    """Serves an HTML page via HTTP. The content can be a static string,
    a string from the input queue, or a template with substitutions.
    """

    def handle_get(self, handler):
        """Sends the current HTML content as a response."""
        with self._lock:
            body = self.current_html
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body.encode('utf-8'))

    def action(self, i):
        """Process incoming messages from the input queue to update the HTML content."""
        instr = self.input_queue.get()
        if instr:
            try:
                # Try to parse as JSON
                variables = json.loads(instr)
                with self._lock:
                    self.variables.update(variables)
                    self.current_html = self.template.format(**self.variables)
            except json.JSONDecodeError:
                # Use as plain HTML content
                with self._lock:
                    self.current_html = instr

    def __init__(self, name="http_output", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'
        self.datatype_in = 'string'
        self._lock = threading.Lock()

        # Server configuration
        self.port = args.get("port", 8080)
        self.path = args.get("path", "out")
        self.template = args.get("template", "<html><body>{content}</body></html>")
        self.variables = args.get("variables", {"content":"EMPTY"})
        self.current_html = self.template.format(**self.variables)

        self.service_name = args.get("service_name", "output")
        self.server = get_server("0.0.0.0", self.port, modules_get={self.path: self.handle_get})

    def module_start(self):
        """Starts the server."""
        utils.config.debug_print(f"[{self.name}] Starting HttpOutput on port {self.port}, path {self.path}")
        start_server("0.0.0.0", self.port)
        utils.config.debug_print(f"[{self.name}] HttpOutput started on port {self.port}")

    def module_stop(self):
        """Stops the server."""
        utils.config.debug_print(f"[{self.name}] Stopping HttpOutput on port {self.port}")
        stop_server("0.0.0.0", self.port)
        utils.config.debug_print(f"[{self.name}] HttpOutput stopped")

output_modules_class['http'] = HttpOutput

