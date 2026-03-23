"""Tests for tabterminal.history."""

from pathlib import Path

import pytest

from tabterminal.config import Config
from tabterminal.history import History


class TestHistory:
    def _make_history(self, tmp_path: Path) -> History:
        cfg = Config(config_path=tmp_path / "config.json")
        return History(cfg, history_path=tmp_path / "history")

    def test_empty_history(self, tmp_path):
        h = self._make_history(tmp_path)
        assert h.get_all() == []
        assert h.get_recent(5) == []

    def test_file_history_attribute(self, tmp_path):
        h = self._make_history(tmp_path)
        from prompt_toolkit.history import FileHistory
        assert isinstance(h.file_history, FileHistory)

    def test_get_recent_respects_n(self, tmp_path):
        h = self._make_history(tmp_path)
        # Use append_string to update both the in-memory list and the file.
        for cmd in ["echo a", "echo b", "echo c", "echo d", "echo e"]:
            h.file_history.append_string(cmd)

        recent = h.get_recent(3)
        assert len(recent) == 3

    def test_get_recent_returns_newest_last(self, tmp_path):
        h = self._make_history(tmp_path)
        for cmd in ["cmd1", "cmd2", "cmd3"]:
            h.file_history.append_string(cmd)

        recent = h.get_recent(10)
        # Oldest first ordering: cmd1, cmd2, cmd3
        assert recent[-1] == "cmd3"

    def test_get_all_returns_all(self, tmp_path):
        h = self._make_history(tmp_path)
        commands = ["ls", "pwd", "whoami"]
        for cmd in commands:
            h.file_history.append_string(cmd)

        all_cmds = h.get_all()
        assert set(all_cmds) == set(commands)
