"""Placeholder run command."""


def handle_run(args: list[str]) -> None:
    """Handle run <command> command."""
    if not args:
        print("Usage: run <command>")
        return

    command = " ".join(args)
    print(f"[placeholder] run command: {command}")
    print("Command execution is not implemented yet.")
