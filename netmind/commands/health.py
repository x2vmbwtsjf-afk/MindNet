"""Local shell health command."""


def handle_show_health(args: list[str]) -> None:
    """Handle show health command."""
    if args:
        print("Usage: show health")
        return

    print("MindNet shell health")
    print("- status: healthy")
    print("- ssh_backend: not_configured")
    print("- mode: local_cli_only")
