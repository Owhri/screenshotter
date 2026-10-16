"""Settings, Credential Manager, and the user's authorized local key fallback."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile

from screenshotter.errors import UserError

CREDENTIAL_NAME = "Screenshotter/OpenAI"


def settings_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Screenshotter"


@dataclass(frozen=True)
class Settings:
    model: str = "gpt-6-astra"
    max_output_tokens: int = 16384
    timeout_seconds: int = 300
    reasoning_effort: str = "instant"

    def validate(self) -> None:
        if not isinstance(self.model, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", self.model):
            raise UserError("Enter a valid API model name.")
        if type(self.max_output_tokens) is not int or not 128 <= self.max_output_tokens <= 32768:
            raise UserError("Token budget must be between 128 and 32768 tokens, including reasoning.")
        if type(self.timeout_seconds) is not int or not 10 <= self.timeout_seconds <= 900:
            raise UserError("Request timeout must be between 10 and 900 seconds.")
        if self.reasoning_effort not in ("instant", "auto", "off", "low", "medium", "high", "xhigh", "max"):
            raise UserError("Choose a supported reasoning effort.")


def load_settings() -> Settings:
    file = settings_dir() / "settings.json"
    if not file.exists():
        return Settings()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        # Upgrade the exact old defaults for the requested accuracy-first mode;
        # preserve any custom model, budget, or timeout from older versions.
        if data == {"model": "gpt-4.1-mini", "max_output_tokens": 600, "timeout_seconds": 60}:
            return Settings()
        if "reasoning_effort" not in data:
            data["reasoning_effort"] = "instant" if data.get("model") == "gpt-6-astra" else "auto"
        settings = Settings(**data)
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


def key_file() -> Path:
    return settings_dir() / "api_key.txt"


def saved_key() -> str | None:
    # A fallback file wins over an older credential that could not be updated.
    try:
        if key_file().exists():
            return key_file().read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeError):
        raise UserError("Cannot read %LOCALAPPDATA%\\Screenshotter\\api_key.txt. Check file access.") from None
    return _credential_key()


def _credential_key() -> str | None:
    try:
        import win32cred
        import pywintypes
    except ImportError:
        raise UserError("Windows credential support is missing. Run Setup.cmd again.") from None

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


def validate_key(key: str) -> str:
    key = key.strip().lstrip("\ufeff").strip()
    if not key or any(c.isspace() for c in key) or not key.isascii():
        raise UserError("Paste only the complete API key, without whitespace or a Bearer prefix.")
    if key.startswith("sk-admin-"):
        raise UserError("Admin keys cannot be used for model requests. Use a regular project API key.")
    if key.startswith(("\"", "'", "OPENAI_API_KEY=")):
        raise UserError("Paste only the API key, without quotes or OPENAI_API_KEY=.")
    return key


def load_key_with_source() -> tuple[str, str]:
    # An explicit app setting must win over an unrelated or stale environment key.
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    try:
        stored = saved_key()
    except UserError:
        if env_key:
            return validate_key(env_key), "OPENAI_API_KEY environment variable"
        raise
    if stored:
        source = "local api_key.txt file" if key_file().exists() else "Windows Credential Manager"
        return validate_key(stored), source
    if env_key:
        return validate_key(env_key), "OPENAI_API_KEY environment variable"
    raise UserError("API key is missing. Run Configure.cmd first.")


def load_key() -> str:
    return load_key_with_source()[0]


def save_key(key: str) -> str:
    """Return the storage used, falling back to text if credentials fail."""
    key = validate_key(key)
    if not key_file().exists():
        try:
            _save_credential_key(key)
            return "credential"
        except UserError:
            pass  # The user explicitly authorized a text file if this fails.
    _save_key_file(key)
    return "text"


def _save_key_file(key: str) -> None:
    temporary = None
    try:
        directory = settings_dir()
        directory.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".api-key-", dir=directory)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(key + "\n")
        temporary.replace(key_file())
    except OSError as exc:
        code = getattr(exc, "winerror", None) or exc.errno
        detail = f" (error {code})" if isinstance(code, int) else ""
        raise UserError(
            "Could not save the key in %LOCALAPPDATA%\\Screenshotter\\api_key.txt"
            f"{detail}. Check your account's folder permissions."
        ) from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _save_credential_key(key: str) -> None:
    try:
        import win32cred
        import pywintypes
    except ImportError:
        raise UserError("Windows credential support is missing. Run Setup.cmd again.") from None

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
