"""Command history management for TabTerminal."""

import os
from pathlib import Path
from typing import List, Optional

from prompt_toolkit.history import FileHistory

from .config import Config, get_config_dir


def get_history_path() -> Path:
    """Return the path to the history file."""
    return get_config_dir() / "history"


class History:
    """Manages command history backed by a plain-text file.

    Provides a :class:`prompt_toolkit.history.FileHistory` instance that
    ``prompt_toolkit`` uses natively, plus helpers to read the history as a
    plain Python list for feeding into the AI predictor.
    """

    def __init__(self, config: Config, history_path: Optional[Path] = None) -> None:
        self._max_size: int = config.get("max_history_size", 10000)
        path = history_path or get_history_path()
        self._path = path
        # prompt_toolkit FileHistory keeps the file in sync automatically.
        self._file_history = FileHistory(str(path))

    # ------------------------------------------------------------------
    # prompt_toolkit integration
    # ------------------------------------------------------------------

    @property
    def file_history(self) -> FileHistory:
        """Return the underlying :class:`~prompt_toolkit.history.FileHistory`."""
        return self._file_history

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_recent(self, n: int = 20) -> List[str]:
        """Return the *n* most recent commands (newest last)."""
        strings = self._file_history.get_strings()
        # get_strings() returns oldest-first; take the last n entries.
        return strings[-n:] if n < len(strings) else list(strings)

    def get_all(self) -> List[str]:
        """Return all recorded commands in oldest-first order."""
        return list(self._file_history.get_strings())
