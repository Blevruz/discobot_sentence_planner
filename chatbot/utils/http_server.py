# chatbot/utils/http_server.py
import http.server
#import socketserver
import json
import threading
try:
    import utils.config as config
except:
    # Useful for testing
    import config

"""
We want to have servers use specific IPs and ports, so we'll likely want to
re-use existing servers depending on their ports. 

Current implementation very basic, a re-implementation with more secure libs
would be good

    Each server has its own thread on which it runs with serve_forever()
    Servers are indexed by their IP and port as a single string

    Each server has two dictionaries for POST and GET handlers respectively which are defined BEFORE the thread is started

"""

servers = dict()

def ip_port_to_string(ip, port):
    return ip + ":" + str(port)

class GenericHandler(http.server.BaseHTTPRequestHandler):
    """Generic handler for all servers"""

    def __init__(self, request, client_address, server, modules_get={}, modules_post={}):
        self.modules_get = modules_get
        self.modules_post = modules_post
        super().__init__(request, client_address, server)

    def do_GET(self):
        print(self.path)
        module = self.path.split("/")[1]

        if module in self.modules_get:
            return self.modules_get[module](self)
        else:
            self.send_error(404)

    def do_POST(self):
        module = self.path.split("/")[1]
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        if module in self.modules_post:
            return self.modules_post[module](self,data)
        else:
            self.send_error(404)

def get_server(ip, port, modules_get = {}, modules_post = {}):
    """Create a new server or return one if it already exists"""
    ip_port = ip_port_to_string(ip, port)
    port = int(port)
    if ip_port not in servers:
        servers[ip_port] = {
                "ip": ip,
                "port": port,
                "server": None,
                "thread": None,
                "handler": None,
                "get_handlers": {},
                "post_handlers": {}
                }

    for key in modules_get:
        servers[ip_port]["get_handlers"][key] = modules_get[key]
    for key in modules_post:
        servers[ip_port]["post_handlers"][key] = modules_post[key]
    return servers[ip_port]

def add_handler(ip, port, module_name, handler, get=False, post=False):
    """Add a handler to a server"""
    server = get_server(ip, port)
    if not get and not post:
        config.debug_print("No handlers specified")
    if get:
        server["handler"].modules_get[module_name] = handler
    if post:
        server["handler"].modules_post[module_name] = handler

def _start_server(server):
    ip = server["ip"]
    port = server["port"]
    ip_port = ip_port_to_string(ip, port)
    server["handler"] = lambda r, ca, s: GenericHandler(request = r, client_address = ca, server = s, modules_get = server["get_handlers"], modules_post = server["post_handlers"])
    server["server"] = http.server.HTTPServer((ip, port), servers[ip_port]["handler"])
    server["thread"] = threading.Thread(target=servers[ip_port]["server"].serve_forever)
    server["thread"].start()

def start_servers():
    """Start all servers"""
    for ip_port in servers:
        server = servers[ip_port]
        _start_server(server)


def start_server(ip, port):
    """Start a server"""
    server = get_server(ip, port)
    if server["thread"]:
        if server["thread"].is_alive():
            config.debug_print("Server already running")
            return
    _start_server(server)

def _stop_server(server):
    server["server"].shutdown()
    server["thread"].join()
    server["server"].server_close()

def stop_servers():
    """Stop all servers"""
    for ip_port in servers:
        server = servers[ip_port]
        _stop_server(server)

def stop_server(ip, port):
    """Stop a server"""
    ip_port = ip_port_to_string(ip, port)
    if ip_port in servers:
        _stop_server(servers[ip_port])
    else:
        config.debug_print("Server not found")


if __name__ == "__main__":
    import time
    srv = get_server("127.0.0.1", 8080)
    def testget(self):
        body = json.dumps("Hello").encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    srv["get_handlers"]["test"] = lambda s: testget(s)
    srv["post_handlers"]["test"] = lambda s, x: print(x)
    start_server("127.0.0.1", 8080)
    time.sleep(10)
    stop_server("127.0.0.1", 8080)

