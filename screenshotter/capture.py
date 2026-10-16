"""Capture into memory without an overlay, shutter effect, or saved image."""

from __future__ import annotations

import mss
import mss.tools


def capture(region: tuple[int, int, int, int] | None = None) -> bytes:
    with mss.mss() as screen:
        monitor = screen.monitors[0]
        if region:
            x1, y1, x2, y2 = region
            left = max(min(x1, x2), monitor["left"])
            top = max(min(y1, y2), monitor["top"])
            right = min(max(x1, x2), monitor["left"] + monitor["width"])
            bottom = min(max(y1, y2), monitor["top"] + monitor["height"])
            if right - left < 4 or bottom - top < 4:
                raise ValueError("Selection is too small.")
            monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        shot = screen.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)
