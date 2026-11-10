import sys
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chatbot"))

from output_modules.http import HttpOutput
from utils import http_server


class HttpOutputTests(unittest.TestCase):
    def test_non_ascii_page_is_served_complete(self):
        # Content-Length counted characters instead of bytes, so browsers cut
        # off the end of pages with emoji or dashes: the closing </script>
        # was lost and the page's script never ran.
        template = ("<html><body><h1>\U0001F916 {{title}} — café</h1>"
                    "<script>var done = true;</script></body></html>")
        module = HttpOutput(port=0, path="page", template=template,
                            variables={"title": "Résumé"})
        module.module_start()
        key = http_server.ip_port_to_string("0.0.0.0", 0)
        self.addCleanup(http_server.servers.pop, key)
        self.addCleanup(http_server.stop_server, "0.0.0.0", 0)
        port = http_server.servers[key]["server"].server_address[1]

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/page") as response:
            raw = response.read()
            declared = int(response.headers["Content-Length"])

        self.assertEqual(declared, len(raw))
        self.assertTrue(raw.decode("utf-8").endswith("</script></body></html>"))


if __name__ == "__main__":
    unittest.main()
