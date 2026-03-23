"""AI-powered command prediction for TabTerminal.

Predictions are fetched asynchronously in a background thread so that the
interactive prompt remains responsive even when network latency is high.
"""

import logging
import os
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# How long (seconds) a cached prediction is considered fresh.
_CACHE_TTL = 60.0


class AIPredictor:
    """Calls an OpenAI-compatible chat API to predict terminal commands.

    The predictor is intentionally *optional*: if no API key is configured
    every method silently returns ``None`` so the rest of the application
    keeps working without changes.

    Parameters
    ----------
    config:
        A :class:`~tabterminal.config.Config` instance used to read ``api_key``,
        ``api_base_url``, ``model`` and ``ai_enabled``.
    """

    def __init__(self, config) -> None:
        self._config = config
        self._client = None
        self._lock = threading.Lock()
        # Simple in-memory cache: key -> (result, expiry_timestamp)
        self._cache: Dict[str, Tuple[Optional[str], float]] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return *True* when the AI backend is configured and enabled."""
        if not self._config.get("ai_enabled", True):
            return False
        return bool(self._resolve_api_key())

    def predict_completion(
        self, current_input: str, history: List[str]
    ) -> Optional[str]:
        """Return a predicted completion suffix for *current_input*.

        The returned string should be appended to *current_input* to produce
        the full suggested command.  Returns ``None`` when no suggestion is
        available.
        """
        if not current_input or not self.is_available():
            return None

        cache_key = f"complete:{current_input}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        history_ctx = "\n".join(history[-10:]) if history else "(none)"
        prompt = (
            "You are a terminal command completion assistant.\n"
            "Given the command history and the partial command the user is typing, "
            "predict the rest of the command.\n\n"
            f"Command history (oldest first):\n{history_ctx}\n\n"
            f"Partial command: {current_input}\n\n"
            "Reply with ONLY the completion text to append after the partial command "
            "(do NOT repeat the partial command). "
            "If you are unsure, reply with an empty string."
        )
        result = self._call_api(prompt, max_tokens=60)
        self._set_cache(cache_key, result)
        return result

    def suggest_next_command(self, history: List[str]) -> Optional[str]:
        """Suggest the most likely *next* command based on recent history.

        Returns a complete command string, or ``None``.
        """
        if not history or not self.is_available():
            return None

        cache_key = f"next:{history[-1]}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        history_ctx = "\n".join(history[-5:])
        prompt = (
            "You are a terminal command predictor.\n"
            "Based on these recently executed commands, predict the single most "
            "likely next command the user will run.\n\n"
            f"Recent commands:\n{history_ctx}\n\n"
            "Reply with ONLY the command, nothing else. "
            "If you cannot predict, reply with an empty string."
        )
        result = self._call_api(prompt, max_tokens=80)
        self._set_cache(cache_key, result)
        return result

    def predict_completion_async(
        self,
        current_input: str,
        history: List[str],
        callback: Callable[[Optional[str]], None],
    ) -> None:
        """Run :meth:`predict_completion` in a background thread.

        *callback* is invoked with the result (possibly ``None``) when the
        prediction is ready.
        """
        thread = threading.Thread(
            target=self._async_worker,
            args=(self.predict_completion, (current_input, history), callback),
            daemon=True,
        )
        thread.start()

    def suggest_next_command_async(
        self,
        history: List[str],
        callback: Callable[[Optional[str]], None],
    ) -> None:
        """Run :meth:`suggest_next_command` in a background thread."""
        thread = threading.Thread(
            target=self._async_worker,
            args=(self.suggest_next_command, (history,), callback),
            daemon=True,
        )
        thread.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> Optional[str]:
        return (
            self._config.get("api_key")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("TABTERMINAL_API_KEY")
        )

    def _get_client(self):
        with self._lock:
            if self._client is None:
                api_key = self._resolve_api_key()
                if not api_key:
                    return None
                try:
                    from openai import OpenAI  # type: ignore

                    base_url = self._config.get(
                        "api_base_url", "https://api.openai.com/v1"
                    )
                    self._client = OpenAI(api_key=api_key, base_url=base_url)
                except Exception as exc:  # pragma: no cover
                    log.debug("Failed to create OpenAI client: %s", exc)
                    return None
            return self._client

    def _call_api(self, prompt: str, max_tokens: int = 80) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            response = client.chat.completions.create(
                model=self._config.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            text = response.choices[0].message.content or ""
            return text.strip() or None
        except Exception as exc:
            log.debug("AI API call failed: %s", exc)
            return None

    def _get_cache(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del self._cache[key]
            return None
        return value

    def _set_cache(self, key: str, value: Optional[str]) -> None:
        self._cache[key] = (value, time.monotonic() + _CACHE_TTL)

    @staticmethod
    def _async_worker(func, args, callback):
        try:
            result = func(*args)
        except Exception:  # pragma: no cover
            result = None
        callback(result)
