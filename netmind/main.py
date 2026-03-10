"""Entry point for the MindNet interactive shell."""

from shell import NetMindShell


def main() -> None:
    """Start the interactive shell."""
    NetMindShell().run()


if __name__ == "__main__":
    main()
