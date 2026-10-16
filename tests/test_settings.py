import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from screenshotter.errors import UserError
from screenshotter.settings import Settings, load_key, load_settings, save_key, save_settings, saved_key


class SettingsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": directory.name})
        env.start()
        self.addCleanup(env.stop)

    def test_settings_roundtrip_contains_no_key(self):
        settings = Settings("gpt-4.1-mini", 500, 30)
        save_settings(settings)
        self.assertEqual(load_settings(), settings)
        data = json.loads((self.directory / "Screenshotter" / "settings.json").read_text())
        self.assertEqual(set(data), {"model", "max_output_tokens", "timeout_seconds"})

    def test_invalid_settings_cannot_override_request_limits(self):
        for settings in (Settings(max_output_tokens=0), Settings(max_output_tokens=999999),
                         Settings(timeout_seconds=0), Settings(model="https://somewhere.invalid"),
                         Settings(max_output_tokens=True)):
            with self.subTest(settings=settings), self.assertRaises(UserError):
                save_settings(settings)

    def test_environment_key_takes_priority_without_reading_credential_store(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "example-key"}), patch(
            "screenshotter.settings.saved_key", side_effect=AssertionError("must not read")
        ):
            self.assertEqual(load_key(), "example-key")

    def test_credential_blob_is_utf16_and_never_saved_in_settings(self):
        store = {}

        def write(credential, flags):
            store.update(credential)

        fake = SimpleNamespace(CRED_TYPE_GENERIC=1, CRED_PERSIST_LOCAL_MACHINE=2,
                               CredWrite=Mock(side_effect=write), CredRead=Mock(side_effect=lambda *_: store))
        with patch.dict("sys.modules", {"win32cred": fake, "pywintypes": SimpleNamespace(error=OSError)}):
            save_key("unit-test-key")
            self.assertEqual(saved_key(), "unit-test-key")
        self.assertEqual(store["CredentialBlob"], "unit-test-key".encode("utf-16-le"))
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
