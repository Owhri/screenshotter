"""Use an installed Windows voice and the default audio output device."""

import threading


class Speaker:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._closed = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        self._closed.set()
        self.stop()

    def speak(self, text: str) -> None:
        import pythoncom
        import win32com.client

        if self._closed.is_set():
            return
        self._stop.clear()
        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            if self._closed.is_set():
                del voice
                return
            # SVSFlagsAsync | SVSFIsNotXML: answers stay plain text.
            voice.Speak(text, 1 | 16)
            while not voice.WaitUntilDone(100):
                if self._stop.is_set() or self._closed.is_set():
                    voice.Speak("", 2 | 16)  # SVSFPurgeBeforeSpeak
                    break
            del voice
        finally:
            pythoncom.CoUninitialize()
