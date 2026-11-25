# middle_modules/participant_status.py
"""
participant_status - remember where the participant is, for the supervisor.

The participant-facing pages report their progress (which stage, which task,
how long it lasts) and the WoZ panel shows it in its header.

HTTP surface (on the shared utils.http_server registry, like http_input):
    POST /participant_status   JSON object, sent by the participant pages.
                               Each POST is a complete snapshot that replaces
                               the previous one. Fields (all optional):
                                 stage       str  page path, e.g. "poems_main"
                                 stageLabel  str  human readable stage name
                                 state       str  one of STATES
                                 task        int  1-based task number
                                 taskCount   int  tasks in this stage
                                 taskTitle   str  short description of the task
                                 timeLimit   num  seconds allowed (task / chat)
                               Unknown fields are ignored.
    GET  /participant_status   -> {"status": {...} | null, "server_time": t}
                               `status` also holds `since` (server time at which
                               the snapshot arrived) and `seq`. A client works
                               out the time left as
                               timeLimit - (server_time - since), which does not
                               depend on the clocks of the two browsers agreeing.

This module is deliberately not wired to anything: status updates must not
go through /user_website_input, where messages of unknown type are passed on
to the LLM as system messages.

Arguments:
    port  : port of the shared HTTP server (default 8080)
    host  : interface to bind (default "0.0.0.0")
    path  : URL path (default "participant_status")
"""
import json
import threading
import time

import utils.config
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.http_server import get_server, start_server

# What the participant can be doing. The WoZ page maps these to text.
STATES = ("intro", "waiting", "task", "chatting", "results", "finished")

_MAX_STR = 120


def _clean_str(value):
    return value.strip()[:_MAX_STR] if isinstance(value, str) else None


def _clean_int(value):
    # bool is an int in Python, but never a meaningful count here
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10**6:
        return value
    return None


def _clean_seconds(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and 0 <= value < 10**6:
        return value
    return None


def sanitize_status(data):
    """Keep only the known fields, with the right types. Returns a dict, or
    None when `data` is not a JSON object."""
    if not isinstance(data, dict):
        return None
    cleaners = {
        "stage": _clean_str,
        "stageLabel": _clean_str,
        "state": lambda v: v if v in STATES else None,
        "task": _clean_int,
        "taskCount": _clean_int,
        "taskTitle": _clean_str,
        "timeLimit": _clean_seconds,
    }
    status = {}
    for key, clean in cleaners.items():
        value = clean(data.get(key))
        if value is not None:
            status[key] = value
    return status


def _send_json(handler, code, obj):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


class ParticipantStatus(DummyMiddle):
    """Holds the latest participant status and serves it over HTTP."""

    def __init__(self, name="participant_status", **args):
        super().__init__(name, **args)
        # Everything happens in the HTTP handlers
        self._loop_type = "blocking"

        self._host = args.get("host", "0.0.0.0")
        self._port = args.get("port", 8080)
        self._path = args.get("path", "participant_status")

        self._lock = threading.Lock()
        self._status = None
        self._seq = 0

        get_server(self._host, self._port,
                   modules_get={self._path: self.handle_get},
                   modules_post={self._path: self.handle_post})

    def handle_get(self, handler):
        with self._lock:
            status = dict(self._status) if self._status is not None else None
        _send_json(handler, 200, {"status": status, "server_time": time.time()})

    def handle_post(self, handler, data):
        try:
            status = sanitize_status(json.loads(data))
        except (ValueError, UnicodeDecodeError):
            status = None
        if status is None:
            _send_json(handler, 400, {"status": "error",
                                      "error": "expected a JSON object"})
            return
        with self._lock:
            self._seq += 1
            status["since"] = time.time()
            status["seq"] = self._seq
            self._status = status
        utils.config.debug_print(f"[{self.name}] Participant status: {status}")
        _send_json(handler, 200, {"status": "ok"})

    def module_start(self):
        # The server is shared and may already be running (start_server
        # checks). Stopping it is left to the modules that own it.
        start_server(self._host, self._port)


middle_modules_class["participant_status"] = ParticipantStatus
