"""Windows tray application. Capturing never activates or opens a window."""

from __future__ import annotations

import sys


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Screenshotter requires Windows 11. See README.md for installation.")

    import ctypes as C
    from ctypes import wintypes as W
    import logging
    from logging.handlers import RotatingFileHandler
    import subprocess
    import threading

    import pystray
    from PIL import Image, ImageDraw

    from screenshotter.api import OpenAIChat
    from screenshotter.capture import capture
    from screenshotter.errors import UserError
    from screenshotter.hotkeys import Hotkeys
    from screenshotter.settings import load_key, load_settings, settings_dir
    from screenshotter.speech import Speaker
    from screenshotter.workflow import Workflow

    # Physical pixels, including monitors at different scaling factors.
    user32 = C.WinDLL("user32", use_last_error=True)
    user32.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
    user32.SetProcessDpiAwarenessContext(C.c_void_p(-4))

    kernel32 = C.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]
    kernel32.CreateMutexW.restype = W.HANDLE
    kernel32.CloseHandle.argtypes = [W.HANDLE]
    mutex = kernel32.CreateMutexW(None, False, "Local\\Screenshotter.OpenAI.Background")
    if not mutex:
        raise C.WinError(C.get_last_error())
    if C.get_last_error() == 183:
        kernel32.CloseHandle(mutex)
        user32.MessageBoxW(None, "Screenshotter is already running. Look in the system tray.", "Screenshotter", 0x40)
        return

    speaker = None
    chat = None
    workflow = None
    hotkeys = None
    try:
        directory = settings_dir()
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(directory / "app.log", maxBytes=128_000, backupCount=1, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger("screenshotter").addHandler(handler)
        logging.getLogger("screenshotter").setLevel(logging.INFO)
        try:
            settings = load_settings()
            chat = OpenAIChat(load_key(), settings.model, settings.max_output_tokens,
                              settings.timeout_seconds, settings.reasoning_effort)
        except UserError as exc:
            user32.MessageBoxW(None, str(exc), "Screenshotter — setup needed", 0x40)
            return

        image = Image.new("RGBA", (64, 64), (24, 32, 48, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((10, 14, 54, 48), radius=6, outline="white", width=4)
        draw.ellipse((23, 23, 41, 41), outline=(100, 210, 255), width=4)
        state = {"status": "Starting…"}
        icon = pystray.Icon("screenshotter", image, "Screenshotter")
        closing = threading.Event()

        def status(text):
            if closing.is_set():
                return
            state["status"] = text
            icon.title = ("Screenshotter: " + text)[:127]
            icon.update_menu()

        speaker = Speaker()
        workflow = Workflow(chat.answer, speaker.speak, status)
        capture_lock = threading.Lock()

        def on_capture(region):
            if closing.is_set() or workflow.busy or not capture_lock.acquire(blocking=False):
                return

            def take():
                try:
                    if not closing.is_set():
                        workflow.submit(capture(region))
                except Exception:
                    status("Capture failed. Try a larger selection on the normal Windows desktop.")
                finally:
                    capture_lock.release()

            # Keep the native hook's message loop responsive during PNG encoding.
            threading.Thread(target=take, name="capture", daemon=True).start()

        hotkeys = Hotkeys(on_capture, status, speaker.stop,
                          lambda: not closing.is_set() and not workflow.busy and not capture_lock.locked())

        def configure(_icon, _item):
            subprocess.Popen([sys.executable, "-m", "screenshotter.configure"])

        def quit_app(_icon, _item):
            closing.set()
            chat.close()
            speaker.close()
            hotkeys.stop()
            icon.stop()

        icon.menu = pystray.Menu(
            pystray.MenuItem(lambda _: state["status"], lambda *_: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _: "Resume hotkeys" if hotkeys.paused else "Pause hotkeys", lambda *_: hotkeys.toggle()),
            pystray.MenuItem("Stop speaking (Ctrl+Alt+S)", lambda *_: speaker.stop()),
            pystray.MenuItem("Settings…", configure),
            pystray.MenuItem("Quit", quit_app),
        )

        def setup(tray):
            if not closing.is_set():
                tray.visible = True
                hotkeys.start()

        icon.run(setup=setup)
    finally:
        if chat:
            chat.close()
        if speaker:
            speaker.close()
        if hotkeys:
            hotkeys.stop()
        if workflow:
            # An in-flight network call must finish or time out before exit.
            # close() prevents it from starting speech after Quit.
            workflow.close(wait=True)
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
