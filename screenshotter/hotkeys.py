"""Windows message-loop hotkeys and an invisible, click-blocking selection."""

from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import threading
import time
from typing import Callable

user32 = C.WinDLL("user32", use_last_error=True)
kernel32 = C.WinDLL("kernel32", use_last_error=True)
LRESULT = C.c_ssize_t
HOOKPROC = C.WINFUNCTYPE(LRESULT, C.c_int, W.WPARAM, W.LPARAM)
user32.SetWindowsHookExW.argtypes = [C.c_int, HOOKPROC, W.HINSTANCE, W.DWORD]
user32.SetWindowsHookExW.restype = W.HANDLE
user32.CallNextHookEx.argtypes = [W.HANDLE, C.c_int, W.WPARAM, W.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [W.HANDLE]
kernel32.GetModuleHandleW.argtypes = [W.LPCWSTR]
kernel32.GetModuleHandleW.restype = W.HMODULE
user32.RegisterHotKey.argtypes = [W.HWND, C.c_int, W.UINT, W.UINT]
user32.PostThreadMessageW.argtypes = [W.DWORD, W.UINT, W.WPARAM, W.LPARAM]
user32.SetTimer.argtypes = [W.HWND, C.c_size_t, W.UINT, C.c_void_p]
user32.SetTimer.restype = C.c_size_t
user32.KillTimer.argtypes = [W.HWND, C.c_size_t]
user32.GetMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
user32.GetMessageW.restype = C.c_int

WM_HOTKEY, WM_TIMER, WM_QUIT, WM_SELECTION, WM_TOGGLE = 0x312, 0x113, 0x12, 0x8001, 0x8002


class MouseEvent(C.Structure):
    _fields_ = [("pt", W.POINT), ("mouseData", W.DWORD), ("flags", W.DWORD),
                ("time", W.DWORD), ("dwExtraInfo", C.c_size_t)]


class Hotkeys:
    def __init__(self, on_capture: Callable, status: Callable[[str], None],
                 on_stop_speech: Callable[[], None] = lambda: None,
                 can_capture: Callable[[], bool] = lambda: True) -> None:
        self.on_capture, self.status = on_capture, status
        self.on_stop_speech = on_stop_speech
        self.can_capture = can_capture
        self._stopped = threading.Event()
        self._thread_id = 0
        self._paused = False
        self._selecting = False
        self._dragging = False
        self._cancelled = False
        self._origin = None
        self._selection = None
        self._timer = 0
        self._deadline = 0.0
        self._callback = HOOKPROC(self._mouse)
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)

    def start(self) -> None:
        if not self._stopped.is_set():
            self._thread.start()

    def toggle(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_TOGGLE, 0, 0)

    @property
    def paused(self) -> bool:
        return self._paused

    def _toggle(self) -> None:
        if self._selecting:
            self._cancel()
        if self._paused:
            self._register()
        else:
            user32.UnregisterHotKey(None, 1)
            user32.UnregisterHotKey(None, 2)
        self._paused = not self._paused
        self.status("Paused — 5 types normally" if self._paused else "Ready")

    def stop(self) -> None:
        self._stopped.set()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread.ident is not None:
            self._thread.join(timeout=3)

    def _register(self) -> None:
        registered = []
        for ident, modifiers in ((1, 0x4000), (2, 0x4004)):
            if not user32.RegisterHotKey(None, ident, modifiers, ord("5")):
                for prior in registered:
                    user32.UnregisterHotKey(None, prior)
                raise RuntimeError("The 5 or Shift+5 shortcut is already in use.")
            registered.append(ident)

    def _cancel(self) -> None:
        if self._timer:
            user32.KillTimer(None, self._timer)
            self._timer = 0
        user32.UnregisterHotKey(None, 3)
        if self._dragging:
            # Swallow the corresponding release so it cannot click the app
            # underneath. A cancelled drag must never submit a screenshot.
            self._cancelled = True
        else:
            self._selecting = False
            self._origin = None
        self.status("Selection cancelled")

    def _mouse(self, code, message, data):
        if code >= 0 and self._selecting:
            event = C.cast(data, C.POINTER(MouseEvent)).contents
            if message == 0x201:  # WM_LBUTTONDOWN
                self._dragging = True
                self._origin = (event.pt.x, event.pt.y)
                return 1
            if message == 0x202 and self._dragging:  # WM_LBUTTONUP
                self._dragging = False
                self._selecting = False
                if not self._cancelled:
                    self._selection = (*self._origin, event.pt.x, event.pt.y)
                    user32.PostThreadMessageW(self._thread_id, WM_SELECTION, 0, 0)
                self._origin = None
                self._cancelled = False
                return 1
        return user32.CallNextHookEx(None, code, message, data)

    def _run(self) -> None:
        msg = W.MSG()
        user32.PeekMessageW(C.byref(msg), None, 0, 0, 0)
        self._thread_id = kernel32.GetCurrentThreadId()
        if self._stopped.is_set():
            self._thread_id = 0
            return
        hook = user32.SetWindowsHookExW(14, self._callback, kernel32.GetModuleHandleW(None), 0)
        try:
            if not hook:
                raise C.WinError(C.get_last_error())
            self._register()
            for ident, key in ((4, ord("S")), (5, ord("P"))):
                if not user32.RegisterHotKey(None, ident, 0x4003, key):
                    raise RuntimeError("Ctrl+Alt+S or Ctrl+Alt+P is already in use.")
            self.status("Ready — 5: screen; Shift+5: drag; Esc: cancel selection")
            while True:
                result = user32.GetMessageW(C.byref(msg), None, 0, 0)
                if result == -1:
                    raise C.WinError(C.get_last_error())
                if result == 0:
                    break
                if msg.message == WM_TOGGLE:
                    self._toggle()
                elif msg.message == WM_HOTKEY:
                    if msg.wParam == 4:
                        self.on_stop_speech()
                    elif msg.wParam == 5:
                        self._toggle()
                    elif msg.wParam == 3:
                        self._cancel()
                    elif self._paused or self._selecting or not self.can_capture():
                        continue
                    elif msg.wParam == 1:
                        self.on_capture(None)
                    elif msg.wParam == 2:
                        if not user32.RegisterHotKey(None, 3, 0x4000, 0x1B):
                            self.status("Cannot start selection: Escape shortcut is in use")
                            continue
                        self._cancelled = False
                        self._selecting = True
                        self._deadline = time.monotonic() + 20
                        self._timer = user32.SetTimer(None, 0, 250, None)
                        if not self._timer:
                            self._cancel()
                            continue
                        self.status("Drag a rectangle now (no overlay); Esc cancels; 20 second timeout")
                elif msg.message == WM_TIMER and self._selecting:
                    if time.monotonic() >= self._deadline:
                        self._cancel()
                elif msg.message == WM_SELECTION:
                    if self._timer:
                        user32.KillTimer(None, self._timer)
                        self._timer = 0
                    user32.UnregisterHotKey(None, 3)
                    self.on_capture(self._selection)
        except Exception as exc:
            self.status(f"Hotkeys stopped: {exc}")
        finally:
            if self._timer:
                user32.KillTimer(None, self._timer)
            for ident in (1, 2, 3, 4, 5):
                user32.UnregisterHotKey(None, ident)
            if hook:
                user32.UnhookWindowsHookEx(hook)
            self._thread_id = 0
