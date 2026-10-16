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

    def test_credential_write_uses_text_and_read_decodes_windows_bytes(self):
        store = {}

        def write(credential, flags):
            # Match pywin32 311's WCHAR API contract. A permissive mock would
            # miss the bytes-versus-str bug in the original save implementation.
            if not isinstance(credential["CredentialBlob"], str):
                raise TypeError("CredentialBlob must be text")
            store.update(credential)
            store["CredentialBlob"] = credential["CredentialBlob"].encode("utf-16-le")

        fake = SimpleNamespace(CRED_TYPE_GENERIC=1, CRED_PERSIST_LOCAL_MACHINE=2,
                               CredWrite=Mock(side_effect=write), CredRead=Mock(side_effect=lambda *_: store))
        with patch.dict("sys.modules", {"win32cred": fake, "pywintypes": SimpleNamespace(error=OSError)}):
            save_key("unit-test-key")
            self.assertEqual(saved_key(), "unit-test-key")
        self.assertEqual(store["CredentialBlob"], "unit-test-key".encode("utf-16-le"))
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_credential_permission_error_identifies_storage_without_exposing_key(self):
        class WindowsError(Exception):
            winerror = 5

        fake = SimpleNamespace(CRED_TYPE_GENERIC=1, CRED_PERSIST_LOCAL_MACHINE=2,
                               CredWrite=Mock(side_effect=WindowsError("unit-test-secret-key")))
        with patch.dict("sys.modules", {"win32cred": fake, "pywintypes": SimpleNamespace(error=WindowsError)}):
            with self.assertRaisesRegex(UserError, "Credential Manager.*Windows error 5") as error:
                save_key("unit-test-secret-key")
        self.assertNotIn("unit-test-secret-key", str(error.exception))

    def test_settings_permission_error_identifies_file_step(self):
        with patch.object(Path, "mkdir", side_effect=PermissionError(13, "raw private path")):
            with self.assertRaisesRegex(UserError, "write settings.*error 13") as error:
                save_settings(Settings())
        self.assertNotIn("raw private path", str(error.exception))


if __name__ == "__main__":
    unittest.main()
