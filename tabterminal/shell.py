"""Main interactive shell loop for TabTerminal."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from .ai_predictor import AIPredictor
from .completer import TabTerminalCompleter
from .config import Config
from .history import History

# ---------------------------------------------------------------------------
# Prompt style
# ---------------------------------------------------------------------------

STYLE = Style.from_dict(
    {
        "prompt.cwd": "ansigreen bold",
        "prompt.sep": "ansiwhite",
        "prompt.dollar": "ansicyan bold",
        "history-completion": "ansiblue",
        "executable-completion": "ansiyellow",
        "ai-suggestion": "italic ansibrightblack",
    }
)


def _make_prompt(cwd: str) -> HTML:
    home = str(Path.home())
    display_cwd = cwd.replace(home, "~") if cwd.startswith(home) else cwd
    return HTML(
        f"<prompt.cwd>{display_cwd}</prompt.cwd>"
        "<prompt.sep> </prompt.sep>"
        "<prompt.dollar>❯</prompt.dollar> "
    )


# ---------------------------------------------------------------------------
# Built-in commands
# ---------------------------------------------------------------------------

BUILTINS = {"exit", "quit", "cd", "help", "config", "ai"}


def _run_builtin(cmd: str, args: list, config: Config) -> Optional[int]:
    """Handle built-in shell commands.  Returns exit code or *None* to continue."""
    if cmd in ("exit", "quit"):
        raise SystemExit(0)

    if cmd == "cd":
        target = args[0] if args else str(Path.home())
        try:
            os.chdir(target)
        except FileNotFoundError:
            print(f"cd: {target}: No such file or directory", file=sys.stderr)
            return 1
        except NotADirectoryError:
            print(f"cd: {target}: Not a directory", file=sys.stderr)
            return 1
        return 0

    if cmd == "help":
        _print_help()
        return 0

    if cmd == "config":
        _run_config_cmd(args, config)
        return 0

    if cmd == "ai":
        _run_ai_cmd(args, config)
        return 0

    return None


def _print_help() -> None:
    print(
        "\n"
        "TabTerminal – AI-powered terminal shell\n"
        "========================================\n"
        "\n"
        "Built-in commands:\n"
        "  cd [dir]                 Change the working directory\n"
        "  exit / quit              Exit TabTerminal\n"
        "  help                     Show this help message\n"
        "  config set <key> <val>   Set a configuration value\n"
        "  config get <key>         Show a configuration value\n"
        "  config list              Show all configuration values\n"
        "  ai status                Show AI predictor status\n"
        "  ai key <api_key>         Set the OpenAI API key\n"
        "  ai model <model>         Set the model (e.g. gpt-4)\n"
        "  ai enable / disable      Enable or disable AI predictions\n"
        "\n"
        "Keyboard shortcuts:\n"
        "  Tab                      Trigger completion\n"
        "  Right Arrow / End        Accept inline suggestion\n"
        "  Ctrl+C                   Cancel current input\n"
        "  Ctrl+D                   Exit TabTerminal\n"
        "\n"
        "Environment variables:\n"
        "  OPENAI_API_KEY           OpenAI API key (alternative to 'ai key')\n"
        "  TABTERMINAL_API_KEY      TabTerminal-specific API key override\n"
    )


def _run_config_cmd(args: list, config: Config) -> None:
    if not args or args[0] == "list":
        for k, v in sorted(config.as_dict().items()):
            # Mask the API key.
            display = "***" if k == "api_key" and v else v
            print(f"  {k} = {display!r}")
        return
    if args[0] == "get" and len(args) >= 2:
        key = args[1]
        val = config.get(key)
        if key == "api_key" and val:
            val = "***"
        print(f"  {key} = {val!r}")
        return
    if args[0] == "set" and len(args) >= 3:
        key, val = args[1], args[2]
        config.set(key, val)
        print(f"  {key} saved.")
        return
    print("Usage: config set <key> <val> | config get <key> | config list")


def _run_ai_cmd(args: list, config: Config) -> None:
    if not args or args[0] == "status":
        enabled = config.get("ai_enabled", True)
        key = config.get("api_key") or os.environ.get("OPENAI_API_KEY") or ""
        model = config.get("model", "gpt-3.5-turbo")
        print(f"  AI enabled : {enabled}")
        print(f"  API key    : {'configured' if key else 'not configured'}")
        print(f"  Model      : {model}")
        print(f"  Base URL   : {config.get('api_base_url', 'https://api.openai.com/v1')}")
        return
    if args[0] == "key" and len(args) >= 2:
        config.set("api_key", args[1])
        print("  API key saved.")
        return
    if args[0] == "model" and len(args) >= 2:
        config.set("model", args[1])
        print(f"  Model set to '{args[1]}'.")
        return
    if args[0] == "enable":
        config.set("ai_enabled", True)
        print("  AI predictions enabled.")
        return
    if args[0] == "disable":
        config.set("ai_enabled", False)
        print("  AI predictions disabled.")
        return
    if args[0] == "url" and len(args) >= 2:
        config.set("api_base_url", args[1])
        print(f"  API base URL set to '{args[1]}'.")
        return
    print("Usage: ai status | ai key <api_key> | ai model <model> | ai enable | ai disable | ai url <url>")


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

def _execute(command: str) -> int:
    """Execute *command* via the system shell and return the exit code."""
    try:
        result = subprocess.run(command, shell=True)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error executing command: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# AI next-command banner
# ---------------------------------------------------------------------------

class _AIBanner:
    """Displays an AI-predicted next command banner after each execution."""

    def __init__(self, predictor: AIPredictor) -> None:
        self._predictor = predictor
        self._pending: Optional[str] = None
        self._lock = threading.Lock()

    def start(self, history_strings: list) -> None:
        if not self._predictor.is_available():
            return
        self._predictor.suggest_next_command_async(
            history_strings, self._on_result
        )

    def _on_result(self, suggestion: Optional[str]) -> None:
        with self._lock:
            self._pending = suggestion

    def show_if_ready(self) -> None:
        with self._lock:
            pending = self._pending
            self._pending = None
        if pending:
            print(f"\n  💡 AI suggests: \033[2m{pending}\033[0m\n")


# ---------------------------------------------------------------------------
# Shell entry point
# ---------------------------------------------------------------------------

def run_shell() -> None:
    """Start the interactive TabTerminal shell."""
    config = Config()
    history = History(config)
    completer = TabTerminalCompleter(history.get_all())
    predictor = AIPredictor(config)
    ai_banner = _AIBanner(predictor)

    session: PromptSession = PromptSession(
        history=history.file_history,
        completer=completer,
        auto_suggest=AutoSuggestFromHistory(),
        style=STYLE,
        complete_while_typing=True,
        enable_history_search=True,
    )

    print("TabTerminal – type 'help' for usage, 'exit' to quit.")
    if not predictor.is_available():
        print(
            "  ℹ  AI predictions are disabled. "
            "Run 'ai key <your_openai_key>' to enable them."
        )

    while True:
        try:
            cwd = os.getcwd()
            user_input: str = session.prompt(_make_prompt(cwd))
        except KeyboardInterrupt:
            continue
        except EOFError:
            print()
            break

        command = user_input.strip()
        if not command:
            continue

        tokens = command.split()
        cmd, args = tokens[0], tokens[1:]

        rc = _run_builtin(cmd, args, config)
        if rc is None:
            rc = _execute(command)
        elif isinstance(rc, int) and rc != 0:
            pass  # built-in already printed an error

        # Update completer with fresh history after every command.
        completer.update_history(history.get_all())

        # Fire off an async AI suggestion for the *next* command.
        ai_banner.start(history.get_recent(10))

        # If there is already a ready suggestion from the previous round, show it.
        ai_banner.show_if_ready()
