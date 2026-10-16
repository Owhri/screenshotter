"""One screenshot per API request. No chat history, retries, or audio API."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request

from screenshotter.errors import UserError

ENDPOINT = "https://api.openai.com/v1/responses"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class OpenAIChat:
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini", max_output_tokens: int = 600,
                 timeout: float = 60) -> None:
        self._key = api_key.strip()
        if not self._key or any(c.isspace() for c in self._key):
            raise UserError("Set a valid API key with Configure.cmd.")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self._closed = threading.Event()
        # Never follow a redirect carrying an Authorization header to another host.
        self._opener = urllib.request.build_opener(NoRedirect())

    def close(self) -> None:
        self._closed.set()

    def answer(self, image: bytes, prompt: str) -> str:
        if self._closed.is_set():
            raise UserError("Request cancelled.")
        if not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise UserError("Screenshot is not a PNG image.")
        if len(image) > MAX_IMAGE_BYTES:
            raise UserError("Screenshot is too large. Use Shift+5 to select a smaller area.")
        encoded = base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.model,
            "store": False,
            "max_output_tokens": self.max_output_tokens,
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}", "detail": "high"},
            ]}],
        }
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # Do not display or log response bodies: they may echo input.
            messages = {
                400: "API rejected the request. Check your model setting and try a smaller selection.",
                401: "API key was rejected. Update it with Configure.cmd.",
                403: "API access was denied. Check your project's model access.",
                404: "API model was not found. Check the model in Configure.cmd.",
                429: "API quota or rate limit reached. Check credits and billing before trying again.",
            }
            code = exc.code
            exc.close()
            raise UserError(messages.get(code, f"API returned HTTP {code}. Try again later.")) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise UserError("Cannot reach the API. Check your connection, then try again.") from None
        if self._closed.is_set():
            raise UserError("Request cancelled.")
        if len(body) > MAX_RESPONSE_BYTES:
            raise UserError("API response exceeded the size limit.")
        try:
            result = json.loads(body)
            return extract_answer(result)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise UserError("API returned an unexpected response. No answer was spoken.") from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_answer(result: dict) -> str:
    if result.get("status") != "completed":
        if result.get("incomplete_details", {}).get("reason") == "max_output_tokens":
            raise UserError("Answer exceeded the length limit. Ask fewer questions in one selection.")
        raise UserError("API did not complete the answer. Try again later.")
    texts = []
    for item in result.get("output", []):
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise UserError("The model declined this request.")
            if content.get("type") == "output_text":
                texts.append(content["text"])
    text = "\n".join(texts).strip()
    if not text:
        raise UserError("API returned no answer text.")
    return text
