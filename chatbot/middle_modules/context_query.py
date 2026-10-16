# middle_modules/context_query.py
"""
context_query - read the live LLM context by addressing commands to llm_service.

Wiring (in config "links"):
    - context_query.cmd              -> llm_service.cmd         (sends the QUERY cmd)
    - llm_service.default            -> context_query.responses (fan-out, alongside
                                       llm_output_router) so we see the QUERY response
    - (optional) any trigger        -> context_query.request   (dict: {"op":...})

HTTP surface (uses the shared utils.http_server registry, like http_input/http_output):
    GET  /context_result              -> returns the most recent LIVE context
    POST /context_result  {op,payload}-> APPEND / REPLACE / DELETE / QUERY
    POST /context_query   {op,payload}-> APPEND / REPLACE / DELETE / QUERY
    POST /context_query   {type:system_prompt, content}  -> APPEND system msg
    POST /context_query   {type:assistant_speech, content}-> APPEND assistant msg
"""
import json
import time
import uuid
import threading
import utils.config
from utils.dummy_module import DummyModule
from utils.queues import QueueSlot
from utils.http_server import get_server, start_server, stop_server

try:
    import utils.config as _cfg
except Exception:
    _cfg = utils.config

middle_modules_class = {}

# Shared between the HTTP handlers and the module instance.
class _State:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_result = None   # most recent captured context (dict)
        self.pending_query = False  # a fresh QUERY is in flight


_state = _State()


def _send_json(handler, code, obj):
    """Write a JSON response (works with utils.http_server's GenericHandler)."""
    data = json.dumps(obj).encode('utf-8')
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(data)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(data)


class ContextQuery(DummyModule):
    """Address QUERY (and future) commands to llm_service and capture responses."""

    def __init__(self, name="context_query", **args):
        super().__init__(name, **args)
        # Light enough to run in a thread
        self._loop_type = 'thread'

        # request: trigger to send a command (from HTTP input or another module)
        self._input_queues['request'] = QueueSlot(self, 'input', datatype='dict')
        # responses: matching response from llm_service (fan-out from its output)
        self._input_queues['responses'] = QueueSlot(self, 'input', datatype='dict')
        # cmd: command we send to llm_service
        self._output_queues['cmd'] = QueueSlot(self, 'output', datatype='dict')
        # result: captured context, emitted out for other modules / stdout
        self._output_queues['result'] = QueueSlot(self, 'output', datatype='dict')

        self._port = int(args.get("http_port", 8898))
        self._host = args.get("http_host", "0.0.0.0")

        # utils.http_server keys handlers by path WITHOUT a leading slash
        self._http_path_query = str(args.get("http_path_query", "context_query")).lstrip("/")
        self._http_path_result = str(args.get("http_path_result", "context_result")).lstrip("/")

        # Register our handlers on the SHARED server registry (ip, port) -> the
        # registry reuses the server if another module already serves this port.
        # cmd ids we've sent and are still awaiting a response for.
        self._sent_ids = set()

        # Register our handlers on the SHARED server registry (ip, port) -> the
        # registry reuses the server if another module already serves this port.
        self._server = get_server(self._host, self._port,
                                  modules_get={self._http_path_result: self._http_get_result},
                                  modules_post={self._http_path_query: self._http_post_query,
                                                self._http_path_result: self._http_post_result})

    # ------------------------------------------------------------- HTTP handlers
    def _wait_for_result(self, timeout=2.0):
        """Return the most recent captured context, waiting briefly (bounded)
        for an in-flight QUERY to land so a cold GET still returns live data.
        Keeps the shared single-threaded server from stalling: at most `timeout`
        s, and only when no fresh result is already cached.
        """
        deadline = time.time() + timeout
        while True:
            with _state.lock:
                res = None
                if _state.last_result is not None:
                    res = dict(_state.last_result)
                    res.pop('_fresh', None)
                    _state.last_result = None  # consume so next GET is fresh
            if res is not None:
                return res
            if time.time() >= deadline:
                return None
            time.sleep(0.03)

    def _http_get_result(self, handler):
        """GET /context_result -> LIVE context.
        Triggers a fresh QUERY, then waits briefly for it to land (bounded),
        so the WoZ page always sees current memory even on first load.
        """
        self._trigger("QUERY", {})
        res = self._wait_for_result(timeout=2.0)
        _send_json(handler, 200, res if res is not None else {"status": "empty"})

    def _http_post_query(self, handler, data):
        """POST /context_query {op,payload} or {type:system_prompt|assistant_speech}."""
        _send_json(handler, 200, self._handle_cmd(data))

    def _http_post_result(self, handler, data):
        """POST /context_result {op,payload} (memory ops from the WoZ page)."""
        _send_json(handler, 200, self._handle_cmd(data))

    def _handle_cmd(self, data):
        """Parse a command body, forward it to llm_service, return a fast ack.

        Non-blocking: we trigger the op (the action loop sends the cmd to
        llm_service) and return immediately with the most recent captured state.
        """
        op, payload = "QUERY", {}
        try:
            req = json.loads(data) if data else {}
            if isinstance(req, dict):
                if "op" in req:
                    op = req["op"]
                    payload = req.get("payload", {})
                elif req.get("type") == "system_prompt":
                    op = "APPEND"
                    payload = {"messages": [{"role": "system",
                                             "content": req.get("content", "")}]}
                elif req.get("type") == "assistant_speech":
                    op = "APPEND"
                    payload = {"messages": [{"role": "assistant",
                                             "content": req.get("content", "")}]}
        except (json.JSONDecodeError, TypeError):
            pass

        self._trigger(op, payload)
        with _state.lock:
            res = None
            if _state.last_result is not None:
                res = dict(_state.last_result)
                res.pop('_fresh', None)
        return {"status": "ok", "op": op, "result": res or {}}

    def _trigger(self, op, payload):
        """Ask the action loop to send an op to llm_service (non-blocking)."""
        self._pending_op = op
        self._pending_payload = payload
        self._trigger_event.set()

    # ------------------------------------------------------------- server lifecycle
    def module_start(self):
        _cfg.debug_print(f"[{self.name}] Starting context HTTP on port {self._port}")
        self._trigger_event = threading.Event()
        self._pending_op = "QUERY"
        self._pending_payload = {}
        start_server(self._host, self._port)
        _cfg.debug_print(f"[{self.name}] context HTTP started on :{self._port} "
                         f"(POST /{self._http_path_query}, GET /{self._http_path_result})")
        # Prime the cache with an initial QUERY so the WoZ page's first
        # loadMemory() GET returns the seed context immediately.
        self._trigger("QUERY", {})

    def module_stop(self):
        _cfg.debug_print(f"[{self.name}] Stopping context HTTP on port {self._port}")
        stop_server(self._host, self._port)
        super().module_stop()
    # ------------------------------------------------------------- core loop
    def action(self, i):
        # 1) Send a pending command (from an HTTP handler or a request trigger).
        if getattr(self, '_trigger_event', None) and self._trigger_event.is_set():
            self._trigger_event.clear()
            self._send_cmd(self._pending_op, self._pending_payload)

        if len(self._input_queues['request']) > 0:
            req = self._input_queues['request'].get()
            if isinstance(req, dict):
                self._send_cmd(req.get("op", "QUERY"), req.get("payload", {}))

        # 2) Consume responses/events from llm_service; capture QUERY responses.
        if len(self._input_queues['responses']) > 0:
            msg = self._input_queues['responses'].get()
            if msg:
                # Only "response" messages whose id matches a cmd we sent.
                # (GENERATE token/generation_done events pass through to the router;
                # we ignore them here but must not block it — they share the fan-out
                # queue, so each consumer gets its own copy.)
                if msg.get("type") == "response" and msg.get("id") in self._sent_ids:
                    self._sent_ids.discard(msg["id"])
                    result = msg.get("result")
                    with _state.lock:
                        if result is not None:
                            result = dict(result)
                        if isinstance(result, dict):
                            result["_fresh"] = True
                        _state.last_result = result
                    _cfg.debug_print(f"[{self.name}] Captured context (version="
                                     f"{result.get('version') if result else '?'})")
                    self._output_queues['result'].put(result)

    def _send_cmd(self, op, payload):
        """Build a command addressed to llm_service and put it on our cmd slot."""
        cmd_id = str(uuid.uuid4())
        cmd = {"id": cmd_id, "from": self.name, "op": op, "payload": payload or {}}
        self._sent_ids.add(cmd_id)
        _cfg.debug_print(f"[{self.name}] Sending {op} cmd {cmd_id} to llm_service")
        self._output_queues['cmd'].put(cmd)


middle_modules_class['context_query'] = ContextQuery
