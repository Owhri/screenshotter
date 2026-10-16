"""Selection event behavior with a fake Win32 boundary, without a live hook."""

import ctypes
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class NativeFunction:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return 123


class NativeLibrary:
    def __init__(self):
        self.functions = {}

    def __getattr__(self, name):
        return self.functions.setdefault(name, NativeFunction())


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.native = NativeLibrary()
        spec = importlib.util.spec_from_file_location(
            "selection_test_hotkeys", Path(__file__).parents[1] / "screenshotter" / "hotkeys.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.object(ctypes, "WinDLL", return_value=self.native, create=True), patch.object(
            ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, create=True
        ):
            spec.loader.exec_module(self.module)
        self.hotkeys = self.module.Hotkeys(Mock(), Mock())
        self.hotkeys._selecting = True

    def mouse(self, message, x, y):
        event = self.module.MouseEvent()
        event.pt.x, event.pt.y = x, y
        return self.hotkeys._mouse(0, message, ctypes.addressof(event))

    def test_selection_blocks_clicks_and_posts_exact_coordinates(self):
        self.assertEqual(self.mouse(0x201, -100, 50), 1)
        self.assertEqual(self.mouse(0x202, 40, 150), 1)
        self.assertEqual(self.hotkeys._selection, (-100, 50, 40, 150))
        self.assertFalse(self.hotkeys._selecting)
        self.assertEqual(len(self.native.PostThreadMessageW.calls), 1)
        self.assertEqual(self.native.CallNextHookEx.calls, [])

    def test_cancelling_mid_drag_swallows_release_without_capturing(self):
        self.mouse(0x201, 10, 10)
        self.hotkeys._cancel()
        self.assertEqual(self.mouse(0x202, 70, 80), 1)
        self.assertFalse(self.hotkeys._selecting)
        self.assertIsNone(self.hotkeys._selection)
        self.assertEqual(self.native.PostThreadMessageW.calls, [])
        self.assertEqual(self.native.CallNextHookEx.calls, [])

    def test_cancelling_before_drag_leaves_normal_mouse_input_alone(self):
        self.hotkeys._cancel()
        self.assertEqual(self.mouse(0x201, 10, 10), 123)
        self.assertEqual(len(self.native.CallNextHookEx.calls), 1)
        self.assertEqual(self.native.PostThreadMessageW.calls, [])


if __name__ == "__main__":
    unittest.main()
