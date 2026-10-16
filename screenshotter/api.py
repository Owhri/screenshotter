"""One screenshot per API request. No chat history, retries, or audio API."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from typing import Callable

from screenshotter.errors import UserError
from screenshotter.settings import Settings, validate_key

ENDPOINT = "https://api.openai.com/v1/responses"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class OpenAIChat:
    def __init__(self, api_key: str, model: str = Settings.model,
                 max_output_tokens: int = Settings.max_output_tokens,
                 timeout: float = Settings.timeout_seconds,
                 reasoning_effort: str = Settings.reasoning_effort,
                 key_provider: Callable[[], str] | None = None) -> None:
        self._key = validate_key(api_key)
        self._key_provider = key_provider
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
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
        effort = self.reasoning_effort
        if effort == "instant":
            effort = "off" if self.model.startswith(("gpt-4", "gpt-3.5")) else "none"
        elif effort == "auto":
            effort = "high" if self.model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")) else "off"
        if effort != "off":
            payload["reasoning"] = {"effort": effort}
        result = self._request_json(ENDPOINT, payload)
        try:
            return extract_answer(result)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise UserError("API returned an unexpected response. No answer was spoken.") from None

    def list_models(self) -> list[str]:
        """Read-only authentication check: no screenshots or model generation."""
        result = self._request_json(ENDPOINT.rsplit("/", 1)[0] + "/models")
        try:
            models = result["data"]
            if not isinstance(models, list):
                raise ValueError
            identifiers = [item["id"] for item in models]
            if not all(isinstance(identifier, str) for identifier in identifiers):
                raise ValueError
            return sorted(identifiers)
        except (ValueError, KeyError, TypeError):
            raise UserError("API model check returned an unexpected response.") from None

    def probe_model(self) -> None:
        """Explicit billable check using a generated pixel, never a screen image."""
        from mss.tools import to_png

        pixel = to_png(b"\xff\xff\xff", (1, 1))
        self.answer(pixel, "Reply with only OK.")

    def _request_json(self, endpoint: str, payload: dict | None = None):
        if self._closed.is_set():
            raise UserError("Request cancelled.")
        active_key = validate_key(self._key_provider() if self._key_provider else self._key)
        request = urllib.request.Request(
            endpoint, data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            method="POST" if payload is not None else "GET",
            headers={"Authorization": f"Bearer {active_key}", "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # Read only a known error code. Never show raw bodies/messages,
            # which can include the submitted key or screenshot details.
            known_code = None
            known_param = None
            try:
                error = json.loads(exc.read(65536))
                candidate = error.get("error", {}).get("code")
                if isinstance(candidate, str) and candidate in ERROR_CODES:
                    known_code = candidate
                candidate = error.get("error", {}).get("param")
                if isinstance(candidate, str) and candidate in REJECTED_PARAMS:
                    known_param = candidate
            except (ValueError, TypeError, AttributeError, OSError):
                pass
            messages = {
                400: "API rejected the request. Check model, reasoning effort, and image size in settings.",
                401: "Authentication failed. Test the regular project key in Configure.cmd and check its active source.",
                403: "API access was denied. Check key permissions and project model access. Model checks need Models read access.",
                404: "API model was not found. Check the model in Configure.cmd.",
                429: "API quota or rate limit reached. Check credits and billing before trying again.",
            }
            code = exc.code
            exc.close()
            message = ERROR_CODES[known_code] if known_code else messages.get(code, "Try again later.")
            if code == 400 and known_param:
                message = REJECTED_PARAMS[known_param]
            raise UserError(f"HTTP {code}: {message}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise UserError("Cannot reach the API. Check your connection, then try again.") from None
        if self._closed.is_set():
            raise UserError("Request cancelled.")
        if len(body) > MAX_RESPONSE_BYTES:
            raise UserError("API response exceeded the size limit.")
        try:
            return json.loads(body)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise UserError("API returned an unexpected response. No answer was spoken.") from None


ERROR_CODES = {
    "invalid_api_key": "The submitted key was rejected. Re-enter the complete regular project key in Configure.cmd.",
    "organization_deactivated": "The API organization is deactivated. Check its status with OpenAI support.",
    "invalid_organization": "The API organization is invalid or unavailable to this key. Check project membership.",
    "mismatched_organization": "The key does not match the API organization. Check project membership.",
    "insufficient_permissions": "The key lacks required permissions. Allow Responses write access and Models read access for the check.",
    "model_not_found": "The selected model is unavailable to this project or its name is incorrect.",
    "insufficient_quota": "API credits or quota are exhausted. Check credits and billing.",
    "ip_not_authorized": "The API project does not allow this network's IP address. Check project IP restrictions.",
    "unsupported_value": "A requested setting is unsupported by the selected model. Check model and reasoning effort.",
    "unsupported_parameter": "The selected model does not accept one of the request parameters. Check model and reasoning effort.",
}

REJECTED_PARAMS = {
    "reasoning.effort": "The model rejected reasoning.effort. Instant sends 'none'; use a model supporting 'none' or select another supported effort.",
    "reasoning": "The model rejected reasoning settings. Select Off to use its default behavior without this parameter.",
    "model": "The API rejected the selected model. Check its name, project access, and image support.",
    "max_output_tokens": "The model rejected the token budget. Adjust the budget in Configure.cmd.",
    "input": "The model rejected the input. Check that it supports image inputs through the Responses API.",
    "input[0].content[1].image_url": "The API rejected the image. Try a smaller capture or a model supporting image inputs.",
    "input[0].content[1].detail": "The model rejected the image detail setting. Check its image-input support.",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_answer(result: dict) -> str:
    if result.get("status") != "completed":
        if result.get("incomplete_details", {}).get("reason") == "max_output_tokens":
            raise UserError("Answer or reasoning exceeded the length limit. Increase the token budget or select fewer questions.")
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
