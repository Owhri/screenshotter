"""Background workflow, independent of the desktop and chat integration."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from screenshotter import PROMPT
from screenshotter.errors import UserError

log = logging.getLogger(__name__)


class Workflow:
    """Run one request at a time; never queue unexpected extra screenshots."""

    def __init__(
        self,
        answer: Callable[[bytes, str], str],
        speak: Callable[[str], None],
        status: Callable[[str], None],
    ) -> None:
        self._answer = answer
        self._speak = speak
        self._status = status
        self._lock = threading.Lock()
        self._closed = False
        self._busy = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="answer")

    def submit(self, screenshot: bytes) -> bool:
        # Capture on the hotkey thread, before any chat interaction, so the
        # attached image always depicts what was visible when requested.
        with self._lock:
            if self._closed or self._busy:
                return False
            self._busy = True
            self._executor.submit(self._run, screenshot)
            return True

    def _run(self, screenshot: bytes) -> None:
        try:
            self._status("Sending screenshot…")
            response = self._answer(screenshot, PROMPT).strip()
            if not response:
                raise RuntimeError("Chat returned an empty answer.")
            self._status("Speaking answer…")
            self._speak(response)
            self._status("Ready")
        except Exception as exc:
            # Do not log screenshots, prompts, answers, or credentials.
            log.error("Screenshot request failed (%s)", type(exc).__name__)
            detail = str(exc) if isinstance(exc, UserError) else f"{type(exc).__name__}. See the app instructions."
            self._status(f"Request failed: {detail}")
        finally:
            with self._lock:
                self._busy = False

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    def close(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=True)
