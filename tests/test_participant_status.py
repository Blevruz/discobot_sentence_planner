import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

from middle_modules.participant_status import ParticipantStatus, sanitize_status
from utils import http_server


class SanitizeTests(unittest.TestCase):
    def test_keeps_known_fields(self):
        data = {"stage": "poems_main", "stageLabel": "Poems", "state": "task",
                "task": 2, "taskCount": 5, "taskTitle": "A poem", "timeLimit": 60}
        self.assertEqual(sanitize_status(data), data)

    def test_drops_unknown_fields_and_bad_types(self):
        data = {"stage": 3, "state": "exploding", "task": -1, "taskCount": True,
                "timeLimit": "60", "taskTitle": "ok", "evil": "<script>"}
        self.assertEqual(sanitize_status(data), {"taskTitle": "ok"})

    def test_long_strings_are_truncated(self):
        self.assertEqual(len(sanitize_status({"stage": "x" * 1000})["stage"]), 120)

    def test_not_an_object(self):
        for data in (None, [], "task", 3):
            self.assertIsNone(sanitize_status(data))


class HttpTests(unittest.TestCase):
    """The real module behind a real local server (ephemeral port)."""

    def setUp(self):
        self.module = ParticipantStatus(host="127.0.0.1", port=0)
        self.module.module_start()
        key = http_server.ip_port_to_string("127.0.0.1", 0)
        self.addCleanup(http_server.servers.pop, key)
        self.addCleanup(http_server.stop_server, "127.0.0.1", 0)
        self.url = "http://127.0.0.1:%d/participant_status" % \
            http_server.servers[key]["server"].server_address[1]

    def post(self, body):
        req = urllib.request.Request(
            self.url, data=body if isinstance(body, bytes) else json.dumps(body).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req)

    def get(self):
        with urllib.request.urlopen(self.url) as r:
            return json.load(r)

    def test_no_status_before_first_post(self):
        reply = self.get()
        self.assertIsNone(reply["status"])
        self.assertAlmostEqual(reply["server_time"], time.time(), delta=5)

    def test_latest_snapshot_replaces_previous_one(self):
        self.post({"state": "waiting", "taskCount": 5})
        self.post({"state": "task", "task": 1, "taskCount": 5, "timeLimit": 30})
        status = self.get()["status"]
        self.assertEqual(status["state"], "task")
        self.assertEqual(status["task"], 1)
        self.assertEqual(status["seq"], 2)
        self.assertLessEqual(status["since"], self.get()["server_time"])

    def test_bad_post_is_rejected_and_keeps_old_status(self):
        self.post({"state": "intro"})
        for body in (b"not json", b"[1]", b"\xff\xfe"):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.post(body)
            self.assertEqual(ctx.exception.code, 400)
        self.assertEqual(self.get()["status"]["state"], "intro")


if __name__ == "__main__":
    unittest.main()
