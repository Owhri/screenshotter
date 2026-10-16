"""Non-secret settings on disk; API keys in Windows Credential Manager."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re

from screenshotter.errors import UserError

CREDENTIAL_NAME = "Screenshotter/OpenAI"


def settings_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Screenshotter"


@dataclass(frozen=True)
class Settings:
    model: str = "gpt-4.1-mini"
    max_output_tokens: int = 600
    timeout_seconds: int = 60

    def validate(self) -> None:
        if not isinstance(self.model, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", self.model):
            raise UserError("Enter a valid API model name.")
        if type(self.max_output_tokens) is not int or not 128 <= self.max_output_tokens <= 2000:
            raise UserError("Answer length must be between 128 and 2000 tokens.")
        if type(self.timeout_seconds) is not int or not 10 <= self.timeout_seconds <= 180:
            raise UserError("Request timeout must be between 10 and 180 seconds.")


def load_settings() -> Settings:
    file = settings_dir() / "settings.json"
    if not file.exists():
        return Settings()
    try:
        settings = Settings(**json.loads(file.read_text(encoding="utf-8")))
        settings.validate()
        return settings
    except (OSError, ValueError, TypeError):
        raise UserError("Cannot read settings.json. Run Configure.cmd to save valid settings.") from None


def save_settings(settings: Settings) -> None:
    settings.validate()
    try:
        directory = settings_dir()
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "settings.json.tmp"
        temporary.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
        temporary.replace(directory / "settings.json")
    except OSError as exc:
        code = getattr(exc, "winerror", None) or exc.errno
        detail = f" (error {code})" if isinstance(code, int) else ""
        raise UserError(
            "Could not write settings in %LOCALAPPDATA%\\Screenshotter"
            f"{detail}. Check that your Windows account can write to that folder."
        ) from None


def saved_key() -> str | None:
    import win32cred
    import pywintypes

    try:
        credential = win32cred.CredRead(CREDENTIAL_NAME, win32cred.CRED_TYPE_GENERIC)
    except pywintypes.error as exc:
        if exc.winerror == 1168:  # ERROR_NOT_FOUND
            return None
        raise UserError("Windows Credential Manager could not read the API key.") from None
    blob = credential["CredentialBlob"]
    try:
        return blob.decode("utf-16-le") if isinstance(blob, bytes) else blob
    except UnicodeDecodeError:
        raise UserError("The saved API key is unreadable. Re-enter it in Configure.cmd.") from None


def load_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip() or saved_key()
    if not key:
        raise UserError("API key is missing. Run Configure.cmd first.")
    return key


def save_key(key: str) -> None:
    try:
        import win32cred
        import pywintypes
    except ImportError:
        raise UserError("Windows credential support is missing. Run Setup.cmd again.") from None

    key = key.strip()
    if not key or any(c.isspace() for c in key):
        raise UserError("Enter an API key without whitespace.")
    try:
        win32cred.CredWrite({
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": CREDENTIAL_NAME,
            "UserName": "OpenAI API",
            # pywin32 311 requires str on write and returns UTF-16 bytes on read.
            "CredentialBlob": key,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }, 0)
    except pywintypes.error as exc:
        code = getattr(exc, "winerror", None)
        detail = f" (Windows error {code})" if isinstance(code, int) else ""
        raise UserError(
            f"Windows Credential Manager could not save the API key{detail}. "
            "Check credential-storage permissions for your Windows account."
        ) from None
    except (TypeError, ValueError):
        raise UserError("Windows rejected the credential format. Update the app and rerun Setup.cmd.") from None
