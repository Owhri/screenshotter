import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from screenshotter.capture import capture


class FakeScreen:
    monitors = [{"left": -100, "top": 0, "width": 300, "height": 200}]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def grab(self, monitor):
        self.monitor = monitor
        size = (monitor["width"], monitor["height"])
        return SimpleNamespace(size=size, rgb=b"\x20\x40\x60" * size[0] * size[1])


class CaptureTests(unittest.TestCase):
    @patch("screenshotter.capture.mss.mss", FakeScreen)
    def test_full_screen_returns_decodable_png_with_virtual_desktop_size(self):
        with Image.open(io.BytesIO(capture())) as image:
            self.assertEqual(image.size, (300, 200))
            self.assertEqual(image.getpixel((0, 0)), (32, 64, 96))

    @patch("screenshotter.capture.mss.mss", FakeScreen)
    def test_reverse_drag_and_negative_monitor_coordinates(self):
        with Image.open(io.BytesIO(capture((30, 90, -50, 10)))) as image:
            self.assertEqual(image.size, (80, 80))

    @patch("screenshotter.capture.mss.mss", FakeScreen)
    def test_offscreen_selection_is_clipped(self):
        with Image.open(io.BytesIO(capture((-200, -20, 30, 50)))) as image:
            self.assertEqual(image.size, (130, 50))

    @patch("screenshotter.capture.mss.mss", FakeScreen)
    def test_empty_or_tiny_selection_does_not_capture(self):
        for region in ((1, 1, 1, 1), (0, 0, 2, 50), (300, 300, 400, 400)):
            with self.subTest(region=region), self.assertRaises(ValueError):
                capture(region)


if __name__ == "__main__":
    unittest.main()
