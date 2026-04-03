"""Tests for shell built-in commands."""

import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from tabterminal.config import Config
from tabterminal.shell import _run_builtin, _run_config_cmd, _run_ai_cmd


def _make_config(tmp_path: Path) -> Config:
    return Config(config_path=tmp_path / "config.json")


class TestRunBuiltin:
    def test_unknown_command_returns_none(self, tmp_path):
        cfg = _make_config(tmp_path)
        result = _run_builtin("ls", ["-la"], cfg)
        assert result is None

    def test_cd_changes_directory(self, tmp_path):
        cfg = _make_config(tmp_path)
        original = os.getcwd()
        try:
            rc = _run_builtin("cd", [str(tmp_path)], cfg)
            assert rc == 0
            assert os.getcwd() == str(tmp_path)
        finally:
            os.chdir(original)

    def test_cd_no_args_goes_home(self, tmp_path):
        cfg = _make_config(tmp_path)
        original = os.getcwd()
        try:
            rc = _run_builtin("cd", [], cfg)
            assert rc == 0
            assert os.getcwd() == str(Path.home())
        finally:
            os.chdir(original)

    def test_cd_missing_dir_returns_error(self, tmp_path):
        cfg = _make_config(tmp_path)
        rc = _run_builtin("cd", ["/nonexistent_xyz_path"], cfg)
        assert rc == 1

    def test_exit_raises_system_exit(self, tmp_path):
        cfg = _make_config(tmp_path)
        with pytest.raises(SystemExit):
            _run_builtin("exit", [], cfg)

    def test_quit_raises_system_exit(self, tmp_path):
        cfg = _make_config(tmp_path)
        with pytest.raises(SystemExit):
            _run_builtin("quit", [], cfg)

    def test_help_returns_zero(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        rc = _run_builtin("help", [], cfg)
        assert rc == 0
        captured = capsys.readouterr()
        assert "TabTerminal" in captured.out


class TestConfigCmd:
    def test_list(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_config_cmd([], cfg)
        out = capsys.readouterr().out
        assert "model" in out

    def test_get(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_config_cmd(["get", "model"], cfg)
        out = capsys.readouterr().out
        assert "model" in out

    def test_set(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_config_cmd(["set", "model", "gpt-4"], cfg)
        assert cfg.get("model") == "gpt-4"

    def test_api_key_masked_in_list(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        cfg.set("api_key", "sk-supersecret")
        _run_config_cmd([], cfg)
        out = capsys.readouterr().out
        assert "supersecret" not in out
        assert "***" in out


class TestAICmd:
    def test_status(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_ai_cmd(["status"], cfg)
        out = capsys.readouterr().out
        assert "AI enabled" in out

    def test_set_key(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_ai_cmd(["key", "sk-newkey"], cfg)
        assert cfg.get("api_key") == "sk-newkey"

    def test_set_model(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_ai_cmd(["model", "gpt-4"], cfg)
        assert cfg.get("model") == "gpt-4"

    def test_enable_disable(self, tmp_path, capsys):
        cfg = _make_config(tmp_path)
        _run_ai_cmd(["disable"], cfg)
        assert cfg.get("ai_enabled") is False
        _run_ai_cmd(["enable"], cfg)
        assert cfg.get("ai_enabled") is True
