"""Entry point for ``python -m tabterminal`` and the ``tabterminal`` script."""

import sys


def main() -> None:
    """Launch the TabTerminal interactive shell."""
    from .shell import run_shell

    try:
        run_shell()
    except SystemExit as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
