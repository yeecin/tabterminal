"""Tests for tabterminal.config."""

import json
import os
from pathlib import Path

import pytest

from tabterminal.config import Config, DEFAULT_CONFIG


class TestConfig:
    def test_defaults(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        assert cfg.get("model") == DEFAULT_CONFIG["model"]
        assert cfg.get("max_history_size") == DEFAULT_CONFIG["max_history_size"]
        assert cfg.get("ai_enabled") is True

    def test_get_missing_key_returns_default(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        assert cfg.get("nonexistent", "fallback") == "fallback"
        assert cfg.get("nonexistent") is None

    def test_set_and_get(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        cfg.set("model", "gpt-4")
        assert cfg.get("model") == "gpt-4"

    def test_persistence(self, tmp_path):
        path = tmp_path / "config.json"
        cfg1 = Config(config_path=path)
        cfg1.set("api_key", "test-key-123")

        # Load a fresh instance from the same path.
        cfg2 = Config(config_path=path)
        assert cfg2.get("api_key") == "test-key-123"

    def test_as_dict_is_copy(self, tmp_path):
        cfg = Config(config_path=tmp_path / "config.json")
        d = cfg.as_dict()
        d["model"] = "changed"
        assert cfg.get("model") == DEFAULT_CONFIG["model"]

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("not valid json", encoding="utf-8")
        cfg = Config(config_path=path)
        assert cfg.get("model") == DEFAULT_CONFIG["model"]

    def test_saved_values_merged_with_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        # Write only a subset of keys.
        path.write_text(json.dumps({"model": "gpt-4"}), encoding="utf-8")
        cfg = Config(config_path=path)
        assert cfg.get("model") == "gpt-4"
        # Default keys not in the file should still be present.
        assert cfg.get("ai_enabled") is True
