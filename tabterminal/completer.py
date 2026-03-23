"""Cross-platform command completer for TabTerminal.

Provides three completion sources, merged in priority order:
1. History-based completions – commands the user has typed before.
2. Executable completions  – binaries found on ``PATH``.
3. Path completions        – file-system paths.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from prompt_toolkit.completion import (
    Completer,
    Completion,
    PathCompleter,
    merge_completers,
)
from prompt_toolkit.document import Document


class HistoryCompleter(Completer):
    """Suggest previously entered commands that start with the current input."""

    def __init__(self, history_strings: List[str]) -> None:
        self._history = history_strings

    def update(self, history_strings: List[str]) -> None:
        """Replace the cached history list (called after each command)."""
        self._history = history_strings

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        word = document.text_before_cursor
        if not word:
            return
        seen: set = set()
        # Iterate newest-first so the most recent match appears first.
        for entry in reversed(self._history):
            if entry.startswith(word) and entry != word:
                if entry not in seen:
                    seen.add(entry)
                    yield Completion(
                        entry[len(word):],
                        start_position=0,
                        display=entry,
                        style="class:history-completion",
                    )


class ExecutableCompleter(Completer):
    """Complete executable names found on the system ``PATH``."""

    def __init__(self) -> None:
        self._executables: List[str] = []
        self._refresh()

    def _refresh(self) -> None:
        seen: set = set()
        path_env = os.environ.get("PATH", "")
        for directory in path_env.split(os.pathsep):
            try:
                for name in os.listdir(directory):
                    full = os.path.join(directory, name)
                    if name not in seen and os.access(full, os.X_OK) and os.path.isfile(full):
                        seen.add(name)
                        # On Windows strip common executable suffixes for display.
                        display_name = name
                        if sys.platform == "win32":
                            for ext in (".exe", ".cmd", ".bat", ".com"):
                                if display_name.lower().endswith(ext):
                                    display_name = display_name[: -len(ext)]
                                    break
                        self._executables.append(display_name)
            except OSError:
                continue
        self._executables.sort()

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        # Only complete the first word (the command itself).
        text = document.text_before_cursor
        if " " in text:
            return
        word = text.lstrip()
        if not word:
            return
        for exe in self._executables:
            if exe.startswith(word) and exe != word:
                yield Completion(
                    exe[len(word):],
                    start_position=0,
                    display=exe,
                    style="class:executable-completion",
                )


class TabTerminalCompleter(Completer):
    """Merged completer: history → executables → paths.

    Completions from earlier sources shadow later ones when there is a match.
    """

    def __init__(self, history_strings: Optional[List[str]] = None) -> None:
        self._history_completer = HistoryCompleter(history_strings or [])
        self._executable_completer = ExecutableCompleter()
        self._path_completer = PathCompleter(expanduser=True)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def update_history(self, history_strings: List[str]) -> None:
        """Refresh the history cache used for completions."""
        self._history_completer.update(history_strings)

    # ------------------------------------------------------------------
    # Completer protocol
    # ------------------------------------------------------------------

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        # History completions (full-command prefix match).
        history_results = list(
            self._history_completer.get_completions(document, complete_event)
        )
        if history_results:
            yield from history_results
            return

        # Executable completions (first token only, no space yet).
        if " " not in text.lstrip():
            exe_results = list(
                self._executable_completer.get_completions(document, complete_event)
            )
            if exe_results:
                yield from exe_results
                return

        # Path completions (file/directory arguments).
        yield from self._path_completer.get_completions(document, complete_event)
