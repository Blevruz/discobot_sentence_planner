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
        # Highest context version we have seen a WRITE (APPEND/DELETE/REPLACE)
        # response for. A GET must not serve a QUERY snapshot whose version is
        # below this, otherwise it can return a pre-write snapshot (stale).
        self.min_required_version = 0


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
        self._lock_sse = threading.Lock()
        # Light enough to run in a thread
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
        """Return the LIVE context, waiting briefly (bounded) for a QUERY
        snapshot that is at least as new as any write we have observed.

        Correctness rule: a write (APPEND/DELETE/REPLACE) bumps the context
        version. A GET must never serve a QUERY snapshot whose version is
        *older* than the latest write we have seen, or it would return a
        pre-write (stale) snapshot. We keep waiting until a QUERY snapshot
        with version >= _state.min_required_version lands, then return it.

        Fallback (cold GET, or if the fresh QUERY times out): the most recent
        snapshot we have that satisfies the version floor; else the newest
        snapshot regardless; else None. APPEND/DELETE/REPLACE responses never
        carry messages and are never returned as the context.
        """
        deadline = time.time() + timeout
        best_fallback = None
        while True:
            with _state.lock:
                floor = _state.min_required_version
                candidate = _state.last_result
                res = None
                if candidate is not None and isinstance(candidate, dict) \
                        and "messages" in candidate:
                    cand_version = candidate.get("version") or 0
                    # Accept a snapshot only if it is fresh enough to reflect
                    # every write we have observed.
                    if cand_version >= floor:
                        res = dict(candidate)
                        res.pop('_fresh', None)
                        _state.last_result = None
                    else:
                        # Too old (a newer write happened); hold as fallback
                        # but keep waiting for a fresh QUERY.
                        if best_fallback is None:
                            best_fallback = dict(candidate)
                            best_fallback.pop('_fresh', None)
            if res is not None:
                return res
            if time.time() >= deadline:
                # Timed out: best-effort. Prefer the version-floor snapshot if
                # we ever captured one; else the newest stale snapshot; else None.
                return best_fallback
            time.sleep(0.03)

    def _http_get_result(self, handler):
        """GET /context_result -> LIVE context.

        If a fresh snapshot is already cached (version >= min_required_version),
        return it immediately without triggering a new QUERY.  Only trigger a
        fresh QUERY when the cache is cold or stale, so that SSE wake-ups do
        not create a QUERY -> SSE -> GET -> QUERY feedback loop.
        """
        with _state.lock:
            floor = _state.min_required_version
            cached = _state.last_result
            cached_ver = (cached.get("version") if isinstance(cached, dict) else None)
            has_fresh = (
                cached is not None
                and isinstance(cached, dict)
                and "messages" in cached
                and (cached.get("version") or 0) >= floor
            )
        _cfg.debug_print(f"[{self.name}] GET /context_result: floor={floor} "
                         f"cached_ver={cached_ver} has_fresh={has_fresh}")
        if not has_fresh:
            _cfg.debug_print(f"[{self.name}] GET: triggering fresh QUERY")
            self._trigger("QUERY", {})
        res = self._wait_for_result(timeout=2.0)
        _cfg.debug_print(f"[{self.name}] GET: returning version="
                         f"{(res.get('version') if isinstance(res, dict) else None)}")
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
        self._sse_version = 0
        self._sse_event = threading.Event()
        self._pending_op = "QUERY"
        self._pending_payload = {}
        get_server(self._host, self._port, modules_get={"sse": self._handle_sse})
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
            if msg and msg.get("type") == "response":
                result = msg.get("result")
                # Track the context version from EVERY response we see, not
                # just the ones we sent. APPEND/DELETE/REPLACE responses from
                # other modules carry the bumped version and must advance the
                # SSE signal, otherwise the browser never learns the context
                # changed.
                if isinstance(result, dict):
                    resp_version = result.get("version")
                    version_advanced = False
                    if isinstance(resp_version, int):
                        with _state.lock:
                            if resp_version > _state.min_required_version:
                                _state.min_required_version = resp_version
                                version_advanced = True
                    # Only cache QUERY results (which carry the 'messages'
                    # list) as the live context snapshot, and only for commands
                    # we sent ourselves (so we know the response is a QUERY
                    # result, not some other op).
                    is_ours = msg.get("id") in self._sent_ids
                    if is_ours:
                        self._sent_ids.discard(msg["id"])
                        if "messages" in result:
                            with _state.lock:
                                result = dict(result)
                                result["_fresh"] = True
                                _state.last_result = result
                            _cfg.debug_print(f"[{self.name}] Captured context "
                                             f"(version={result.get('version')})")
                    # Only signal SSE subscribers when the context version
                    # actually advanced (a real change), so that repeated
                    # QUERY responses at the same version do not spam.
                    if version_advanced:
                        with self._lock_sse:
                            self._sse_version += 1
                        _cfg.debug_print(f"[{self.name}] SSE: version advanced to "
                                         f"{self._sse_version}, waking clients")
                        self._sse_event.set()
                    else:
                        _cfg.debug_print(f"[{self.name}] Response at version "
                                         f"{resp_version} (no advance, floor="
                                         f"{_state.min_required_version}, "
                                         f"ours={is_ours})")
                # Always fan the response out so other consumers see it.
                self._output_queues['result'].put(result)


    def _handle_sse(self, handler):
        """GET /sse - Server-Sent Events stream for live context updates.

        Sends an SSE frame every time the context changes (driven by
        _trigger_event). The browser's EventSource fires onmessage for
        each frame; the WoZ page uses this as a wake-up signal to
        re-fetch the context via GET /context_result.
        """
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()

        # Send an initial frame so the browser knows the connection is live.
        handler.wfile.write(b"data: \n\n")
        handler.wfile.flush()

        try:
            my_version = 0
            while True:
                # Wait for a context change (or 30s timeout for keepalive).
                self._sse_event.wait(timeout=30)
                # Clear the event so the next wait() blocks until a new
                # version bump.  If two bumps happen between two wake-ups,
                # the version check below still catches the latest one.
                self._sse_event.clear()
                # Check if the context version has advanced past ours.
                with self._lock_sse:
                    current = self._sse_version
                if current > my_version:
                    my_version = current
                    _cfg.debug_print(f"[{self.name}] SSE: sending frame "
                                     f"(version {my_version})")
                    handler.wfile.write(b"data: \n\n")
                    handler.wfile.flush()
                else:
                    # No new version (timeout or spurious wakeup): send a
                    # keepalive comment to prevent proxy/browser timeout.
                    handler.wfile.write(b": keepalive\n\n")
                    handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Client disconnected

    def _send_cmd(self, op, payload):
        """Build a command addressed to llm_service and put it on our cmd slot."""
        cmd_id = str(uuid.uuid4())
        cmd = {"id": cmd_id, "from": self.name, "op": op, "payload": payload or {}}
        self._sent_ids.add(cmd_id)
        _cfg.debug_print(f"[{self.name}] Sending {op} cmd {cmd_id} to llm_service")
        self._output_queues['cmd'].put(cmd)


middle_modules_class['context_query'] = ContextQuery
