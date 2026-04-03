"""Configuration management for TabTerminal."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "api_base_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo",
    "ai_enabled": True,
    "ai_suggestion_delay": 0.8,
    "max_history_size": 10000,
    "show_ai_indicator": True,
    "prompt_style": "default",
}


def get_config_dir() -> Path:
    """Return the TabTerminal configuration directory, creating it if needed."""
    config_dir = Path.home() / ".tabterminal"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


class Config:
    """Manages TabTerminal configuration persisted in ~/.tabterminal/config.json."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._path = config_path or (get_config_dir() / "config.json")
        self._data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return a configuration value, falling back to *default*."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Persist a configuration value."""
        self._data[key] = value
        self._save()

    def as_dict(self) -> Dict[str, Any]:
        """Return a copy of the full configuration dictionary."""
        return dict(self._data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load configuration from disk, merging with defaults."""
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as fh:
                    saved = json.load(fh)
                if isinstance(saved, dict):
                    self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        """Write current configuration to disk."""
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass
