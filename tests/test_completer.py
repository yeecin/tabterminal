"""Tests for tabterminal.completer."""

from prompt_toolkit.document import Document

from tabterminal.completer import (
    ExecutableCompleter,
    HistoryCompleter,
    TabTerminalCompleter,
)


class TestHistoryCompleter:
    def _completions(self, completer, text):
        doc = Document(text, len(text))
        return list(completer.get_completions(doc, None))

    def test_empty_input_yields_nothing(self):
        hc = HistoryCompleter(["ls -la", "git status"])
        assert self._completions(hc, "") == []

    def test_prefix_match(self):
        hc = HistoryCompleter(["git status", "git commit -m 'msg'", "ls"])
        results = self._completions(hc, "git")
        texts = [r.text + "git" for r in results]  # reconstruct full command
        # Both git commands should appear.
        assert len(results) == 2

    def test_exact_match_excluded(self):
        hc = HistoryCompleter(["git status"])
        results = self._completions(hc, "git status")
        assert results == []

    def test_update_replaces_history(self):
        hc = HistoryCompleter(["old command"])
        hc.update(["new command"])
        results = self._completions(hc, "new")
        assert len(results) == 1

    def test_no_duplicates(self):
        hc = HistoryCompleter(["git status", "git status", "git status"])
        results = self._completions(hc, "git")
        assert len(results) == 1


class TestExecutableCompleter:
    def _completions(self, completer, text):
        doc = Document(text, len(text))
        return list(completer.get_completions(doc, None))

    def test_no_completions_with_space(self):
        ec = ExecutableCompleter()
        # After a space we are in argument territory – no executable completions.
        results = self._completions(ec, "ls ")
        assert results == []

    def test_python_is_found(self):
        ec = ExecutableCompleter()
        # 'python' or 'python3' should be on PATH in the test environment.
        results = self._completions(ec, "pyth")
        names = [r.display for r in results]
        # At least one python variant should complete.
        assert any("python" in str(n).lower() for n in names)


class TestTabTerminalCompleter:
    def _completions(self, completer, text):
        doc = Document(text, len(text))
        return list(completer.get_completions(doc, None))

    def test_history_completions_take_priority(self):
        tc = TabTerminalCompleter(history_strings=["git status", "git log"])
        results = self._completions(tc, "git")
        styles = [r.style for r in results]
        # All results should be history completions.
        assert all("history" in s for s in styles)

    def test_update_history(self):
        tc = TabTerminalCompleter(history_strings=[])
        tc.update_history(["docker ps", "docker images"])
        results = self._completions(tc, "docker")
        assert len(results) == 2

    def test_no_completions_for_empty_input(self):
        tc = TabTerminalCompleter(history_strings=["git status"])
        # Empty input falls through to the PathCompleter which shows
        # current directory entries – that is expected shell behaviour.
        # Verify that history completions are NOT included (no prefix match).
        results = self._completions(tc, "")
        styles = [r.style for r in results]
        assert not any("history" in s for s in styles)
