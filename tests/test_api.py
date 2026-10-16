import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

from screenshotter import PROMPT
from screenshotter.api import OpenAIChat
from screenshotter.errors import UserError
from screenshotter.workflow import Workflow

PNG = b"\x89PNG\r\n\x1a\nimage-data"


def completed(text="42"):
    return {"status": "completed", "output": [{"type": "message", "role": "assistant", "content": [
        {"type": "output_text", "text": text},
    ]}]}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.requests.append((self.path, self.headers.get("Authorization"), json.loads(data)))
        self.send_response(self.server.status)
        for key, value in self.server.extra_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(self.server.body)

    def do_GET(self):
        self.server.get_requests.append(self.path)
        self.send_response(500)
        self.end_headers()

    def log_message(self, *_):
        pass


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.status = 200
        self.server.body = json.dumps(completed()).encode()
        self.server.extra_headers = {}
        self.server.requests = []
        self.server.get_requests = []
        # Production always uses HTTPS api.openai.com. Only tests redirect it.
        self.endpoint_patch = patch("screenshotter.api.ENDPOINT", f"http://127.0.0.1:{self.server.server_port}/v1/responses")
        self.endpoint_patch.start()
        self.addCleanup(self.endpoint_patch.stop)
        self.client = OpenAIChat("unit-test-not-a-real-key")

    def test_http_image_request_to_spoken_answer(self):
        spoken = []
        workflow = Workflow(self.client.answer, spoken.append, lambda _: None)
        workflow.submit(PNG)
        workflow.close()
        self.assertEqual(spoken, ["42"])
        self.assertEqual(len(self.server.requests), 1)
        path, authorization, payload = self.server.requests[0]
        self.assertEqual(path, "/v1/responses")
        self.assertEqual(authorization, "Bearer unit-test-not-a-real-key")
        self.assertEqual(payload["model"], "gpt-4.1-mini")
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["max_output_tokens"], 600)
        self.assertEqual(len(payload["input"]), 1)
        content = payload["input"][0]["content"]
        self.assertEqual(content[0], {"type": "input_text", "text": PROMPT})
        prefix, data = content[1]["image_url"].split(",", 1)
        self.assertEqual(prefix, "data:image/png;base64")
        self.assertEqual(base64.b64decode(data), PNG)
        self.assertEqual(content[1]["detail"], "high")

    def test_rate_limit_is_actionable_and_never_retried(self):
        self.server.status = 429
        self.server.body = b'{"error": {"message": "secret raw server details"}}'
        with self.assertRaisesRegex(UserError, "credits and billing") as error:
            self.client.answer(PNG, PROMPT)
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(len(self.server.requests), 1)

    def test_rejected_key_is_actionable_without_echoing_server_body(self):
        self.server.status = 401
        self.server.body = b'unit-test-not-a-real-key'
        with self.assertRaisesRegex(UserError, "Configure.cmd") as error:
            self.client.answer(PNG, PROMPT)
        self.assertNotIn("unit-test-not-a-real-key", str(error.exception))

    def test_redirect_is_not_followed(self):
        self.server.status = 302
        self.server.extra_headers = {"Location": "/leak"}
        with self.assertRaisesRegex(UserError, "HTTP 302"):
            self.client.answer(PNG, PROMPT)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.get_requests, [])

    def test_incomplete_answer_is_not_presented_as_complete(self):
        result = completed("This is only half an answer")
        result.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        self.server.body = json.dumps(result).encode()
        with self.assertRaisesRegex(UserError, "length limit"):
            self.client.answer(PNG, PROMPT)

    def test_refusal_is_not_silently_spoken_as_an_answer(self):
        self.server.body = json.dumps({"status": "completed", "output": [{
            "type": "message", "role": "assistant", "content": [{"type": "refusal", "refusal": "No"}],
        }]}).encode()
        with self.assertRaisesRegex(UserError, "declined"):
            self.client.answer(PNG, PROMPT)

    def test_malformed_or_empty_response_has_no_answer(self):
        for body in (b"not json", b"null", b"[]", b'{"status":"completed","output":[]}',
                     b'{"status":"completed","output":[null]}'):
            with self.subTest(body=body):
                self.server.body = body
                with self.assertRaises(UserError):
                    self.client.answer(PNG, PROMPT)

    def test_closed_client_or_invalid_image_never_sends(self):
        with self.assertRaisesRegex(UserError, "not a PNG"):
            self.client.answer(b"not an image", PROMPT)
        self.client.close()
        with self.assertRaisesRegex(UserError, "cancelled"):
            self.client.answer(PNG, PROMPT)
        self.assertEqual(self.server.requests, [])

    def test_connection_timeout_is_safe_and_not_retried(self):
        with patch.object(self.client._opener, "open", side_effect=TimeoutError) as request:
            with self.assertRaisesRegex(UserError, "connection"):
                self.client.answer(PNG, PROMPT)
        request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
