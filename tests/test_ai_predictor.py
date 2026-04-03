"""Tests for tabterminal.ai_predictor."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tabterminal.ai_predictor import AIPredictor
from tabterminal.config import Config


def _make_predictor(tmp_path: Path, extra: dict = None) -> AIPredictor:
    cfg = Config(config_path=tmp_path / "config.json")
    if extra:
        for k, v in extra.items():
            cfg.set(k, v)
    return AIPredictor(cfg)


class TestAIPredictorAvailability:
    def test_not_available_without_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TABTERMINAL_API_KEY", raising=False)
        predictor = _make_predictor(tmp_path)
        assert predictor.is_available() is False

    def test_available_with_env_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        assert predictor.is_available() is True

    def test_not_available_when_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path, {"ai_enabled": False})
        assert predictor.is_available() is False

    def test_available_with_config_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TABTERMINAL_API_KEY", raising=False)
        predictor = _make_predictor(tmp_path, {"api_key": "sk-config-key"})
        assert predictor.is_available() is True


class TestAIPredictorPredictions:
    def _mock_client(self, response_text: str):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = response_text
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    def test_predict_completion_returns_none_when_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TABTERMINAL_API_KEY", raising=False)
        predictor = _make_predictor(tmp_path)
        result = predictor.predict_completion("git ", ["git status"])
        assert result is None

    def test_predict_completion_returns_none_for_empty_input(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        result = predictor.predict_completion("", ["git status"])
        assert result is None

    def test_predict_completion_uses_api(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        predictor._client = self._mock_client("status --short")

        result = predictor.predict_completion("git ", ["git status"])
        assert result == "status --short"

    def test_predict_completion_caches_result(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        mock_client = self._mock_client("status")
        predictor._client = mock_client

        predictor.predict_completion("git ", [])
        predictor.predict_completion("git ", [])
        # API should only be called once thanks to caching.
        assert mock_client.chat.completions.create.call_count == 1

    def test_suggest_next_command_returns_none_without_history(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        result = predictor.suggest_next_command([])
        assert result is None

    def test_suggest_next_command_uses_api(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        predictor._client = self._mock_client("git push")

        result = predictor.suggest_next_command(["git add .", "git commit -m 'fix'"])
        assert result == "git push"

    def test_api_failure_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("network error")
        predictor._client = mock_client

        result = predictor.predict_completion("git ", [])
        assert result is None

    def test_predict_completion_async_calls_callback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        predictor = _make_predictor(tmp_path)
        predictor._client = self._mock_client("log --oneline")

        received = []

        def callback(result):
            received.append(result)

        predictor.predict_completion_async("git ", [], callback)
        # Wait for the background thread.
        timeout = 5.0
        start = time.time()
        while not received and (time.time() - start) < timeout:
            time.sleep(0.05)

        assert received == ["log --oneline"]
