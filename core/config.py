from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from core import constants
from core.exceptions import ConfigurationError


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_value(env: dict[str, str], key: str, default: str) -> str:
    return os.getenv(key) or env.get(key) or default


def _get_bool(env: dict[str, str], key: str, default: bool) -> bool:
    value = _get_value(env, key, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment and optional .env."""

    project_root: Path
    assistant_name: str
    ollama_base_url: str
    main_model: str
    log_level: str
    default_mode: str
    max_history_messages: int
    data_dir: Path
    log_dir: Path
    voice_enabled: bool
    tts_enabled: bool
    whisper_model_size: str
    piper_executable: str
    piper_voice: str
    browser_headless: bool
    require_confirmation_for_medium: bool
    require_confirmation_for_high: bool

    @classmethod
    def load(cls, project_root: Path | None = None) -> "Settings":
        root = (project_root or Path(__file__).resolve().parents[1]).resolve()
        env = _load_dotenv(root / ".env")
        max_history_raw = _get_value(env, "MAX_HISTORY_MESSAGES", str(constants.DEFAULT_MAX_HISTORY_MESSAGES))
        try:
            max_history = int(max_history_raw)
        except ValueError as exc:
            raise ConfigurationError("MAX_HISTORY_MESSAGES must be an integer") from exc
        if max_history < 2:
            raise ConfigurationError("MAX_HISTORY_MESSAGES must be at least 2")

        settings = cls(
            project_root=root,
            assistant_name=_get_value(env, "ASSISTANT_NAME", constants.DEFAULT_ASSISTANT_NAME),
            ollama_base_url=_get_value(env, "OLLAMA_BASE_URL", constants.DEFAULT_OLLAMA_BASE_URL).rstrip("/"),
            main_model=_get_value(env, "OLLAMA_MAIN_MODEL", constants.DEFAULT_MAIN_MODEL),
            log_level=_get_value(env, "LOG_LEVEL", constants.DEFAULT_LOG_LEVEL).upper(),
            default_mode=_get_value(env, "DEFAULT_MODE", constants.DEFAULT_MODE).lower(),
            max_history_messages=max_history,
            data_dir=root / constants.DATA_DIR,
            log_dir=root / constants.LOG_DIR,
            voice_enabled=_get_bool(env, "ENABLE_VOICE", False),
            tts_enabled=_get_bool(env, "ENABLE_TTS", False),
            whisper_model_size=_get_value(env, "WHISPER_MODEL_SIZE", "base"),
            piper_executable=_get_value(env, "PIPER_EXECUTABLE", "piper"),
            piper_voice=_get_value(env, "PIPER_VOICE", ""),
            browser_headless=_get_bool(env, "BROWSER_HEADLESS", False),
            require_confirmation_for_medium=_get_bool(env, "CONFIRM_MEDIUM_RISK", True),
            require_confirmation_for_high=_get_bool(env, "CONFIRM_HIGH_RISK", True),
        )
        settings.ensure_directories()
        return settings

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
